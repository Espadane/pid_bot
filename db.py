from sqlalchemy import create_engine, MetaData, Table, String, Integer,\
    Column
from sqlalchemy.ext.declarative import declarative_base
from logger import logger
from sqlalchemy.orm import Session
import random

try:
    engine = create_engine('sqlite:///database.db')
    Base = declarative_base()
except Exception as error:
    logger.warning(error)


class Tasks(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer(), nullable=False)
    user_name = Column(String(100), nullable=False)
    task_type = Column(String(100), nullable=False)
    task_category = Column(String(100), nullable=False)
    task_body = Column(String(100), nullable=False)
    approved = Column(Integer(), default=0)


try:
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
except Exception as error:
    logger.warning(error)


def insert_request_to_db(task_data: dict) -> None:
    """
        Вставляем значения в базу данных.
    """
    tasks = Tasks(
        user_id=task_data['user_id'],
        user_name=task_data['user_name'],
        task_type=task_data['task_type'],
        task_category=task_data['task_category'],
        task_body=task_data['task_body'],
    )
    try:
        session.add(tasks)
        session.commit()
        logger.debug('Данные добавленны в базу')
    except Exception as error:
        logger.warning(error)


def get_new_task_from_db() -> dict:
    """
        Получаем новые не подтвержденные задания из базы
    """
    try:
        new_tasks = session.query(Tasks).filter(Tasks.approved == 0).first()
    except Exception as error:
        logger.warning('error')

    return new_tasks


async def get_new_tasks_count() -> int:
    """
        получаем количество новых не подтвержденных задач
    """
    try:
        new_tasks_count = session.query(Tasks).filter(
            Tasks.approved == 0).count()
    except Exception as error:
        logger.warning(error)

    return int(new_tasks_count)


def approve_task():
    """
        меняем статус задачи на подтверждено
    """
    try:
        first_task = get_new_task_from_db()
    except Exception as error:
        logger.warning(error)
    try:
        first_task.approved = 1
        session.add(first_task)
        session.commit()
    except Exception as error:
        logger.warning(error)


def delete_task():
    """
        удаляем не подтвержденную задачу
    """
    try:
        fist_task = get_new_task_from_db()
        session.delete(fist_task)
        session.commit()
    except Exception as error:
        logger.warning(error)


def get_random_task(task_category: str, task_type: str) -> str:
    """
        получаем случайную подтвержденную задачу из базы
    """
    tasks = session.query(Tasks).filter(Tasks.approved == 1,
                                        Tasks.task_category == task_category,
                                        Tasks.task_type == task_type).all()
    try:
        random_task = random.choice(tasks).task_body
    except Exception:
        random_task = 'В базе нет подходящего задания'

    return random_task
