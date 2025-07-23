
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, Engine, PrimaryKeyConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, DeclarativeBase
from typing import Any, TYPE_CHECKING, Dict
if TYPE_CHECKING:
    from ..format import GeneralInfo
else:
    GeneralInfo = Dict
    
Base: DeclarativeBase = declarative_base()

class SchoolInfo(Base): #type:ignore
    __tablename__ = "school"
    id = Column(Integer, primary_key=True)
    
    name = Column(String)
    education_type = Column(String)
    school_type = Column(String)
    direct_management_agency = Column(String)
    symbol = Column(String)
    english_name = Column(String)
    website = Column(String)
    fallback_website = Column(String)
    location = Column(String)
    education_quality_assurance_organization = Column(String)
    qa_issue_date = Column(String)
    qa_expire_date = Column(String)

class Document(Base): #type:ignore
    __tablename__ = "document"
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    school_id = Column(Integer)
    url = Column(String)
    doc_index = Column(Integer)

    title = Column(String)
    html = Column(String)
    text = Column(String)
    
class TravelLog(Base): #type:ignore
    __tablename__ = "travel_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    school_id = Column(Integer, nullable=False)
    travel_index = Column(Integer, nullable=False)
    
    valid = Column(Boolean)
    score = Column(Float)
    retry = Column(Integer)
    from_url = Column(String)
    url = Column(String)
    
class ErrorLog(Base): #type:ignore
    __tablename__ = "error_log"
    school_id = Column(Integer, nullable=False)
    travel_index = Column(Integer, nullable=False)
    retry = Column(Integer, nullable=False)
    
    time = Column(String)
    from_url = Column(String)
    url = Column(String)
    content = Column(String)
    
    __table_args__ = (
        PrimaryKeyConstraint("school_id", "travel_index", "retry"),
    )
    
def create(url: str, echo: bool = False) -> Engine:
    engine = create_engine(url, echo=echo)
    Base.metadata.create_all(engine)
    return engine
def add_schools(url: str, data: GeneralInfo):
    engine = create_engine(url, echo=False)
    session = sessionmaker(bind=engine)()
    for info in data:
        school = SchoolInfo()
        school.id = int(info["Id"]) #type:ignore
        school.name = info["Tên trường"] #type:ignore
        school.education_type = info["Loại hình cơ sở đào tạo"] #type:ignore
        school.school_type = info["Loại trường"] #type:ignore
        school.direct_management_agency = info["Cơ quan quản lý trực tiếp"] #type:ignore
        school.symbol = info["Ký hiệu"] #type:ignore
        school.english_name = info["Tên tiếng Anh"] #type:ignore
        school.website = info["Website"] #type:ignore
        school.fallback_website = "" #type:ignore
        school.location = info["Tỉnh, thành phố"] #type:ignore
        school.education_quality_assurance_organization = info["Được kiểm định bởi tổ chức kiểm định chất lượng giáo dục"] #type:ignore
        school.qa_issue_date = info.get("Ngày cấp giấy chứng nhận kiểm định chất lượng", "") #type:ignore
        school.qa_expire_date = info.get("Ngày hết hạn giá trị của giấy chứng nhận kiểm định chất lượng", "") #type:ignore
        session.add(school)
    session.commit()
    session.close()
    engine.dispose()
if __name__ == "__main__":
    engine = create("sqlite:///data/sqlite/test.db", echo=True)
    engine.dispose()