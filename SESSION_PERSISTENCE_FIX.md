# Telegram Session Persistence Fix

## Problem Summary

**Issue**: Telegram session gets disconnected and doesn't persist between app restarts. Users have to re-authenticate every time.

## Root Cause

The problem was in the `/api/telegram/config` endpoint in `backend/app/api/telegram.py`.

### What Was Happening:

1. **Initial Authentication**: When you verify the phone code, the `session_string` is correctly saved to the database
2. **Updating Channels**: When you select/deselect monitored channels, the frontend calls `/api/telegram/config`
3. **Session Lost**: This endpoint was **creating a NEW config record** instead of updating the existing one
4. **No Session String**: The new record didn't include the `session_string`, so it was lost!

### Original Buggy Code:

```python
@router.post("/config")
async def create_telegram_config(config: TelegramConfigCreate, db: Session = Depends(get_db)):
    # Deactivate existing configs
    db.query(TelegramConfig).update({"is_active": False})
    
    # Create NEW config WITHOUT session_string ❌
    db_config = TelegramConfig(
        api_id=config.api_id,
        api_hash=config.api_hash,
        phone_number=config.phone_number,
        monitored_chats=json.dumps(config.monitored_chats),
        is_active=True
        # session_string is NOT included! ❌
    )
    db.add(db_config)
    db.commit()
```

## The Fix

Changed the endpoint to **UPDATE the existing config** instead of creating a new one, which **preserves the session_string**.

### New Fixed Code:

```python
@router.post("/config")
async def create_telegram_config(config: TelegramConfigCreate, db: Session = Depends(get_db)):
    # Try to find existing config first
    existing_config = db.query(TelegramConfig).filter(TelegramConfig.is_active).first()
    
    if existing_config:
        # Update existing config and PRESERVE session_string ✅
        existing_config.api_id = config.api_id
        existing_config.api_hash = config.api_hash
        existing_config.phone_number = config.phone_number
        existing_config.monitored_chats = json.dumps(config.monitored_chats)
        # session_string is preserved automatically ✅
        db.commit()
        db.refresh(existing_config)
        return existing_config
    else:
        # Create new config only if none exists
        db_config = TelegramConfig(...)
        db.add(db_config)
        db.commit()
        return db_config
```

## How Session Persistence Works Now

1. **First Time Setup**:
   - Enter API credentials → Save
   - Verify phone code → `session_string` saved to database

2. **Updating Monitored Channels**:
   - Select/deselect channels → Click "Save & Update"
   - Endpoint **updates** existing config
   - `session_string` is **preserved**

3. **App Restart**:
   - Backend loads config from database
   - `session_string` is still there ✅
   - Telegram client reconnects automatically
   - No re-authentication needed!

## Testing the Fix

1. **Initial Setup**:
   ```bash
   # Start the app
   .\start.ps1
   
   # Complete Telegram authentication
   # - Enter API credentials
   # - Verify phone code
   # - Select channels
   ```

2. **Test Persistence**:
   ```bash
   # Stop the backend (Ctrl+C)
   # Restart the backend
   .\start.ps1
   
   # Check status - should show "Connected" without re-authentication
   ```

3. **Verify Database**:
   ```python
   # Run this to check the database
   python backend/check_db.py
   ```

## Additional Improvements

### Logging Added
The fix includes helpful logging:
- ✅ "Updated Telegram config (ID: X), session_string preserved: True"
- ✅ "Created new Telegram config (ID: X)"

This helps you verify that the session is being preserved properly.

## Why This Happened

The original code was designed for a "create only" workflow where you'd set up Telegram once and never change it. But in practice:
- Users need to add/remove monitored channels frequently
- Each channel update was destroying and recreating the config
- This lost the precious `session_string` that keeps you authenticated

## What's Different Now

✅ **Before**: Every channel update = new config record = lost session  
✅ **After**: Channel updates = update existing config = session preserved

## Files Modified

- `backend/app/api/telegram.py` - Fixed `/config` endpoint to update instead of recreate

## Date Fixed

December 27, 2025
