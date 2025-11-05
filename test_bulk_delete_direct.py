#!/usr/bin/env python3
"""
Testing new bulk deletion functionality for scheduled broadcasts.
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
    message_content = Column(Text, nullable=False)  # JSON string with message content
    scheduled_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    admin_id = Column(Integer, nullable=False)  # ID of admin who created the broadcast


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


def get_scheduled_broadcasts_by_admin(db, admin_id: int):
    """Gets all scheduled broadcasts for a specific admin."""
    return db.query(ScheduledBroadcast).filter(
        ScheduledBroadcast.admin_id == admin_id,
        ScheduledBroadcast.is_sent == False  # noqa: E712
    ).order_by(ScheduledBroadcast.scheduled_datetime).all()


def delete_scheduled_messages(db, broadcast_ids: list[int], batch_size: int = 50) -> tuple[int, int, list[int]]:
    """
    Deletes scheduled broadcasts in batches with retry logic and logging.
    
    Args:
        db: Database session
        broadcast_ids: List of broadcast IDs to delete
        batch_size: Size of batch for deletion (default 50)
        
    Returns:
        tuple: (successfully deleted, errors, list of failed IDs)
    """
    import time
    import logging
    logger = logging.getLogger(__name__)
    
    if not broadcast_ids:
        print("Broadcast ID list is empty, no deletion needed")
        return 0, 0, []
    
    total_success = 0
    total_errors = 0
    failed_ids = []
    
    print(f"Starting bulk deletion of {len(broadcast_ids)} scheduled broadcasts")
    
    # Split the ID list into batches
    for i in range(0, len(broadcast_ids), batch_size):
        batch = broadcast_ids[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(broadcast_ids) + batch_size - 1)//batch_size}, size: {len(batch)}")
        
        # Try to delete the batch
        batch_success = 0
        batch_errors = 0
        
        # First check which broadcasts exist
        existing_broadcasts = db.query(ScheduledBroadcast.id).filter(
            ScheduledBroadcast.id.in_(batch)
        ).all()
        
        existing_ids = [b.id for b in existing_broadcasts]
        not_found_ids = [bid for bid in batch if bid not in existing_ids]
        
        if not_found_ids:
            print(f"Broadcasts with IDs {not_found_ids} not found for deletion")
            batch_errors += len(not_found_ids)
            failed_ids.extend(not_found_ids)
        
        # Delete existing broadcasts
        if existing_ids:
            try:
                deleted_count = db.query(ScheduledBroadcast).filter(
                    ScheduledBroadcast.id.in_(existing_ids)
                ).delete(synchronize_session=False)
                
                db.commit()
                batch_success += deleted_count
                print(f"Successfully deleted {deleted_count} broadcasts from batch")
                
            except Exception as e:
                print(f"Error deleting batch {existing_ids}: {e}")
                db.rollback()
                batch_errors += len(existing_ids)
                failed_ids.extend(existing_ids)
        
        total_success += batch_success
        total_errors += batch_errors
        
        # Add a small pause between batches to avoid overloading the DB
        time.sleep(0.1)
    
    print(f"Bulk deletion completed: {total_success} successful, {total_errors} errors")
    
    return total_success, total_errors, failed_ids


def delete_scheduled_messages_by_admin(db, admin_id: int, batch_size: int = 50) -> tuple[int, int, list[int]]:
    """
    Deletes all scheduled broadcasts for a specific admin.
    
    Args:
        db: Database session
        admin_id: Admin ID
        batch_size: Size of batch for deletion (default 50)
        
    Returns:
        tuple: (successfully deleted, errors, list of failed IDs)
    """
    print(f"Starting deletion of all scheduled broadcasts for admin {admin_id}")
    
    # Get all broadcast IDs for the admin
    broadcast_ids = [
        broadcast.id for broadcast in 
        db.query(ScheduledBroadcast.id).filter(
            ScheduledBroadcast.admin_id == admin_id
        ).all()
    ]
    
    if not broadcast_ids:
        print(f"No scheduled broadcasts found for admin {admin_id}")
        return 0, 0, []
    
    print(f"Found {len(broadcast_ids)} scheduled broadcasts for admin {admin_id}")
    
    # Perform bulk deletion
    return delete_scheduled_messages(db, broadcast_ids, batch_size)


def test_bulk_delete_functionality():
    """
    Tests the bulk deletion functionality for scheduled broadcasts.
    """
    print("=== Testing Bulk Deletion Functionality ===")
    
    # Create tables
    create_tables()
    
    # Create session
    db = SessionLocal()
    
    try:
        # Create test data
        admin_id = 123456789  # Test admin ID
        
        print(f"Creating test broadcasts for admin {admin_id}...")
        
        # Delete any existing test broadcasts for this admin
        existing_broadcasts = db.query(ScheduledBroadcast).filter(
            ScheduledBroadcast.admin_id == admin_id
        ).all()
        
        for broadcast in existing_broadcasts:
            db.delete(broadcast)
        db.commit()
        
        # Create 60 test broadcasts
        test_broadcasts = []
        for i in range(60):
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
        
        # Test bulk deletion of specific IDs
        ids_to_delete = test_broadcasts[:30]  # Delete first 30
        print(f"Deleting {len(ids_to_delete)} broadcasts via delete_scheduled_messages...")
        
        success_count, error_count, failed_ids = delete_scheduled_messages(db, ids_to_delete)
        print(f"Deletion by ID: success={success_count}, errors={error_count}, failed={failed_ids}")
        
        # Check remaining broadcasts
        remaining_broadcasts = get_scheduled_broadcasts_by_admin(db, admin_id)
        print(f"After ID deletion: {len(remaining_broadcasts)} broadcasts remaining")
        
        # Test deletion of all admin broadcasts
        print("Deleting all remaining broadcasts via delete_scheduled_messages_by_admin...")
        success_count, error_count, failed_ids = delete_scheduled_messages_by_admin(db, admin_id)
        print(f"Delete all: success={success_count}, errors={error_count}, failed={failed_ids}")
        
        # Check that all broadcasts were deleted
        final_broadcasts = get_scheduled_broadcasts_by_admin(db, admin_id)
        print(f"After deleting all: {len(final_broadcasts)} broadcasts remaining")
        
        if len(final_broadcasts) == 0:
            print("[SUCCESS] Test passed! All broadcasts were deleted.")
        else:
            print("[FAILURE] Test failed! Not all broadcasts were deleted.")
    
    finally:
        db.close()
    
    print("[END] Testing Completed ===")


if __name__ == "__main__":
    test_bulk_delete_functionality()