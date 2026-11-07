# 从sqlalchemy库里导入需要的东西
# create_engine：用来连接数据库
# Column：定义表的列
# Integer/String/Text/Date/Boolean：数据类型
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, Boolean

# 导入declarative_base，这是所有表的基类
from sqlalchemy.ext.declarative import declarative_base

# 导入sessionmaker，用来创建和数据库对话的会话
from sqlalchemy.orm import sessionmaker

# 读取本地配置（账号/密码/主机/库名从环境变量或 .env 取，不在代码里写死）
from config import get

# 连接MySQL数据库：mysql+pymysql:// 是固定写法
# 配置项见 .env.example；若密码含特殊字符，需要做 URL 编码
DB_USER = get("DB_USER", "root")
DB_PASSWORD = get("DB_PASSWORD", "")
DB_HOST = get("DB_HOST", "localhost")
DB_NAME = get("DB_NAME", "job_db")
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")

# 创建一个会话工厂，以后用它来打开数据库连接
SessionLocal=sessionmaker(bind=engine)

#创建基类，我们的表都要继承它
Base=declarative_base()

#定义投递记录表，对应DBeaver里建的applications表
class Application(Base):
    #告诉数据库这个类对应的表名
    __tablename__="applications"
    #id列：整数类型，主键，自动递增
    id=Column(Integer, primary_key=True,autoincrement=True)
    #company列：公司名，最长100个字符
    company=Column(String(100))
    #position列：岗位名，最长100个字符
    position=Column(String(100))
    status = Column(String(50))
    #status列：下一步要做什么
    next_step=Column(String(200))
    #apply_date列：投递日期
    apply_date=Column(Date)


#定义面试题表，对应DBeaver里的interview_questions表
class Question(Base):
    __tablename__="interview_questions"
    id=Column(Integer, primary_key=True,autoincrement=True)#主键自增
    question=Column(Text)#题目内容，长文本
    answer=Column(Text)#答案长文本
    category = Column(String(50))  # 分类：Python/FastAPI/MySQL
    mastered = Column(Boolean, default=False)  # 掌握了吗，默认没掌握


#定义岗位表，存所有招聘信息
class Job(Base):
    __tablename__="jobs"
    id=Column(Integer, primary_key=True,autoincrement=True)#主键自增
    company=Column(String(100))#公司名
    position=Column(String(100))#岗位名
    city=Column(String(50))#城市
    salary=Column(String(50))#薪资
    priority=Column(String(10))#优先级 P0/P1/P2
    job_type=Column(String(20))#类型：实习/秋招正式
    is_soe=Column(Boolean, default=False)#是不是国企央企
    url=Column(String(500))#岗位链接
    description=Column(Text)#岗位描述


## 运行这行会自动在数据库里建表（你已经用DBeaver建过了，这行不会覆盖）
Base.metadata.create_all(engine)
