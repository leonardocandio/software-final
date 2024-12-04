import logging
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import date, datetime
from typing import List, Optional
import os

# Create logs directory if it doesn't exist
os.makedirs("/app/logs", exist_ok=True)

# Database connection
SQLALCHEMY_DATABASE_URL = "postgresql://root:pass@db/db"
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

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    tickets = relationship("Ticket", back_populates="user")

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    concert_id = Column(Integer, ForeignKey("concerts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    purchase_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="available")
    concert = relationship("Concert", back_populates="tickets")
    user = relationship("User", back_populates="tickets")

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

@app.post("/users/", response_model=dict)
async def create_user(
    email: str,
    name: str,
    db: Session = Depends(get_db)
):
    user = User(email=email, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User created successfully", "user_id": user.id}

@app.post("/tickets/reserve/", response_model=dict)
async def reserve_ticket(
    concert_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    today = date.today().strftime("%d_%m_%Y")
    log_filename = f"/app/logs/log_{today}.log"
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )   

    concert = db.query(Concert).filter(Concert.id == concert_id).first()
    if not concert:
        logging.error(f"Error en ejecucion")
        raise HTTPException(status_code=404, detail="Concert not found")
    
    if concert.available_tickets <= 0:
        raise HTTPException(status_code=400, detail="No tickets available")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    ticket = Ticket(
        concert_id=concert_id,
        user_id=user_id,
        status="reserved"
    )
    concert.available_tickets -= 1
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logging.info(f"Exito en ejecucion")
    
    return {
        "message": "Ticket reserved successfully",
        "ticket_id": ticket.id
    }

@app.post("/tickets/purchase/{ticket_id}", response_model=dict)
async def purchase_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket.status == "purchased":
        raise HTTPException(status_code=400, detail="Ticket already purchased")
    
    ticket.status = "purchased"
    ticket.purchase_date = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Ticket purchased successfully"}

@app.post("/tickets/cancel/{ticket_id}", response_model=dict)
async def cancel_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket.status == "available":
        raise HTTPException(status_code=400, detail="Ticket is already available")
    
    if ticket.status == "used":
        raise HTTPException(status_code=400, detail="Used tickets cannot be cancelled")
    
    concert = db.query(Concert).filter(Concert.id == ticket.concert_id).first()
    concert.available_tickets += 1
    ticket.status = "available"
    ticket.user_id = None
    
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

@app.post("/tickets/{ticket_id}/use", response_model=dict)
async def use_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket.status != "purchased":
        raise HTTPException(status_code=400, detail="Ticket must be purchased before use")
    
    ticket.status = "used"
    db.commit()
    
    return {"message": "Ticket marked as used"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

