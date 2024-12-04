from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import List, Optional
import os

# Database connection
SQLALCHEMY_DATABASE_URL = "postgresql://root:pass@db/root"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Concert(Base):
    __tablename__ = "concerts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    date = Column(DateTime)
    venue = Column(String)
    total_tickets = Column(Integer)
    available_tickets = Column(Integer)
    price = Column(Float)
    tickets = relationship("Ticket", back_populates="concert")

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    concert_id = Column(Integer, ForeignKey("concerts.id"))
    user_email = Column(String)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    is_cancelled = Column(Boolean, default=False)
    concert = relationship("Concert", back_populates="tickets")

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API endpoints
@app.post("/concerts/", response_model=dict)
async def create_concert(
    name: str,
    date: datetime,
    venue: str,
    total_tickets: int,
    price: float,
    db: Session = Depends(get_db)
):
    concert = Concert(
        name=name,
        date=date,
        venue=venue,
        total_tickets=total_tickets,
        available_tickets=total_tickets,
        price=price
    )
    db.add(concert)
    db.commit()
    db.refresh(concert)
    return {"message": "Concert created successfully", "concert_id": concert.id}

@app.post("/tickets/purchase/", response_model=dict)
async def purchase_ticket(
    concert_id: int,
    user_email: str,
    db: Session = Depends(get_db)
):
    concert = db.query(Concert).filter(Concert.id == concert_id).first()
    if not concert:
        raise HTTPException(status_code=404, detail="Concert not found")
    
    if concert.available_tickets <= 0:
        raise HTTPException(status_code=400, detail="No tickets available")
    
    ticket = Ticket(
        concert_id=concert_id,
        user_email=user_email
    )
    concert.available_tickets -= 1
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    return {
        "message": "Ticket purchased successfully",
        "ticket_id": ticket.id
    }

@app.post("/tickets/cancel/{ticket_id}", response_model=dict)
async def cancel_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket.is_cancelled:
        raise HTTPException(status_code=400, detail="Ticket already cancelled")
    
    concert = db.query(Concert).filter(Concert.id == ticket.concert_id).first()
    concert.available_tickets += 1
    ticket.is_cancelled = True
    
    db.commit()
    
    return {"message": "Ticket cancelled successfully"}

@app.get("/concerts/", response_model=List[dict])
async def list_concerts(db: Session = Depends(get_db)):
    concerts = db.query(Concert).all()
    return [
        {
            "id": concert.id,
            "name": concert.name,
            "date": concert.date,
            "venue": concert.venue,
            "available_tickets": concert.available_tickets,
            "price": concert.price
        }
        for concert in concerts
    ]

