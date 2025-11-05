#!/usr/bin/env python3
"""
Testing optimized single scheduled broadcast deletion function.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


# Create in-memory database for testing
engine = create_engine('sqlite:///:memory:', echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Define ScheduledBroadcast model for testing
class ScheduledBroadcast(Base):
    __tablename__ = "scheduled_broadcasts"
    
    id = Column(Integer, primary_key=True, index=True)
    message_content = Column(Text, nullable=False) # JSON string with message content
    scheduled_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    admin_id = Column(Integer, nullable=False) # ID of admin who created the broadcast


def create_tables():
    """Creates tables in database."""
    Base.metadata.create_all(bind=engine)


def create_scheduled_broadcast(db, admin_id: int, message_content: str, scheduled_datetime: datetime):
    """Creates a new scheduled broadcast."""
    scheduled_broadcast = ScheduledBroadcast(
        admin_id=admin_id,
        message_content=message_content,
        scheduled_datetime=scheduled_datetime
    )
    db.add(scheduled_broadcast)
    db.commit()
    db.refresh(scheduled_broadcast)
    return scheduled_broadcast


def delete_scheduled_broadcast(db, broadcast_id: int):
    """Deletes a scheduled broadcast (optimized version)."""
    print(f"Attempting to delete broadcast with ID: {broadcast_id}")
    
    try:
        # Direct deletion of record by ID with return of number of changed rows
        deleted_count = db.query(ScheduledBroadcast).filter(
            ScheduledBroadcast.id == broadcast_id
        ).delete(synchronize_session=False)
        
        if deleted_count > 0:
            db.commit()
            print(f"Broadcast with ID {broadcast_id} successfully deleted from database")
            return True
        else:
            db.rollback()  # Optional rollback if nothing was deleted
            print(f"Broadcast with ID {broadcast_id} not found for deletion")
            return False
            
    except Exception as e:
        print(f"Error deleting broadcast with ID {broadcast_id}: {e}")
        db.rollback()
        return False


def get_scheduled_broadcasts_by_admin(db, admin_id: int):
    """Gets all scheduled broadcasts for a specific admin."""
    return db.query(ScheduledBroadcast).filter(
        ScheduledBroadcast.admin_id == admin_id,
        ScheduledBroadcast.is_sent == False  # noqa: E712
    ).order_by(ScheduledBroadcast.scheduled_datetime).all()


def test_single_delete_performance():
    """
    Tests the performance of deleting individual broadcasts.
    """
    print("=== Testing Performance of Individual Broadcast Deletions ===")
    
    # Create tables
    create_tables()
    
    # Create session
    db = SessionLocal()
    
    try:
        # Create test data - 10 broadcasts
        admin_id = 123456789 # Test admin ID
        
        print(f"Creating 100 test broadcasts for admin {admin_id}...")
        
        # Delete any existing test broadcasts for this admin
        existing_broadcasts = db.query(ScheduledBroadcast).filter(
            ScheduledBroadcast.admin_id == admin_id
        ).all()
        
        for broadcast in existing_broadcasts:
            db.delete(broadcast)
        db.commit()
        
        # Create 100 test broadcasts
        test_broadcasts = []
        for i in range(100):
            scheduled_time = datetime.now() + timedelta(days=i+1)
            message_content = json.dumps({"text": f"Test message {i}", "message_id": i+1})
            
            broadcast = create_scheduled_broadcast(
                db=db,
                admin_id=admin_id,
                message_content=message_content,
                scheduled_datetime=scheduled_time
            )
            test_broadcasts.append(broadcast.id)
        
        print(f"Created {len(test_broadcasts)} test broadcasts")
        
        # Verify broadcasts were created
        stored_broadcasts = get_scheduled_broadcasts_by_admin(db, admin_id)
        print(f"Check: {len(stored_broadcasts)} broadcasts in database")
        
        # Test deleting 50 broadcasts one by one
        ids_to_delete = test_broadcasts[:50]  # Delete first 50
        print(f"Deleting {len(ids_to_delete)} broadcasts one by one...")
        
        success_count = 0
        for broadcast_id in ids_to_delete:
            if delete_scheduled_broadcast(db, broadcast_id):
                success_count += 1
        
        print(f"Successfully deleted: {success_count} out of {len(ids_to_delete)}")
        
        # Check remaining broadcasts
        remaining_broadcasts = get_scheduled_broadcasts_by_admin(db, admin_id)
        print(f"After deletion: {len(remaining_broadcasts)} broadcasts remaining")
        
        if len(remaining_broadcasts) == 50:
            print("[SUCCESS] Test passed! All individual broadcasts were correctly deleted.")
        else:
            print("[FAILURE] Test failed! Number of remaining broadcasts does not match expected.")
    
    finally:
        db.close()
    
    print("=== Testing Completed ===")


if __name__ == "__main__":
    test_single_delete_performance()