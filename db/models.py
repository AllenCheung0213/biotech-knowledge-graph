from sqlalchemy import Column, Integer, String, Date, Text, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Company(Base):
    __tablename__ = 'companies'
    company_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    type = Column(String(50), default='unknown')
    founded_year = Column(Integer)
    website = Column(String(255))
    employee_count = Column(Integer)
    hq_location = Column(String(255))
    external_ids = Column(JSON)

    layoff_events = relationship('LayoffEvent', back_populates='company')
    funding_rounds  = relationship('FundingRound', back_populates='company')

class LayoffEvent(Base):
    __tablename__ = 'layoff_events'
    layoff_id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.company_id'), nullable=False)
    date = Column(Date, nullable=False)
    num_laid_off = Column(Integer)
    percent_laid_off = Column(Float)
    description = Column(Text)
    source_url = Column(String(512))

    company = relationship('Company', back_populates='layoff_events')

class Investor(Base):
    __tablename__ = 'investors'
    investor_id = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(255), unique=True, nullable=False)
    type       = Column(String(100))
    external_ids = Column(JSON)

    funding_rounds = relationship('FundingRoundInvestor', back_populates='investor')

class FundingRound(Base):
    __tablename__ = 'funding_rounds'
    round_id   = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.company_id'), nullable=False)
    date       = Column(Date)
    round_type = Column(String(50))
    amount     = Column(Float)
    details    = Column(Text)

    company = relationship('Company', back_populates='funding_rounds')
    investors = relationship('FundingRoundInvestor', back_populates='round')

class FundingRoundInvestor(Base):
    __tablename__ = 'funding_round_investors'
    id          = Column(Integer, primary_key=True, autoincrement=True)
    round_id    = Column(Integer, ForeignKey('funding_rounds.round_id'), nullable=False)
    investor_id = Column(Integer, ForeignKey('investors.investor_id'), nullable=False)

    round    = relationship('FundingRound', back_populates='investors')
    investor = relationship('Investor', back_populates='funding_rounds')