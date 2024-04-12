from datetime import datetime
import os
from typing import List
from sqlalchemy import create_engine, DateTime, Engine, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm.session import Session


DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///sql.db')


def get_engine(echo:bool=True) -> Engine:
    return create_engine(DATABASE_URI, echo=echo)


class Base(DeclarativeBase):
    pass


class PromoCode(Base):
    __tablename__ = 'promo_code_reference'
    code: Mapped[str] = mapped_column(primary_key=True)
    description: Mapped[str]

    def __repr__(self) -> str:
        return f"{self.code}"
    
    def get_all() -> List["PromoCode"]:
        with Session(get_engine(echo=False)) as session:
            return session.query(PromoCode).all()
    

def calculate_total_cost():
    return 100.00

class HotelRate(Base):
    __tablename__ = 'hotel_rate'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hotel_name: Mapped[str]
    check_in_date: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    check_out_date: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    search_url: Mapped[str]
    promo_code: Mapped[str] = mapped_column(ForeignKey('promo_code_reference.code'), nullable=True)
    nightly_rate: Mapped[float]

    def __repr__(self) -> str:
        return f"{self.hotel_name}: ({self.check_in_date.isoformat()[:10]} - {self.check_out_date.isoformat()[:10]} @ ${self.nightly_rate}/night with '{self.promo_code})'"
    
    def get_all() -> List["HotelRate"]:
        with Session(get_engine(echo=False)) as session:
            return session.query(HotelRate).order_by(HotelRate.check_in_date, HotelRate.promo_code, HotelRate.check_out_date).all()


if __name__ == '__main__':
    engine = get_engine(echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(get_engine(echo=False)) as session:
        session.add_all([
            PromoCode(code='', description='Default'),
            PromoCode(code='ZEMPUS', description='Friends & Family'),
            PromoCode(code='ZEMPUR', description='UOTM Red Carpet'),
        ])
        session.commit()
