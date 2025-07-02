#!/usr/bin/env python3
"""
Local test script for CalDAV integration debugging.
Tests connectivity and calendar discovery with calendar.mail.ru.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta

# Add the caldav library path
sys.path.insert(0, '../caldav')

import caldav
from caldav.lib.error import PropfindError, DAVError, AuthorizationError

# Test credentials for calendar.mail.ru
CALDAV_URL = "https://calendar.mail.ru"
USERNAME = "maxim.makarov@vk.team"
PASSWORD = "ItZQKzldmbc3I0wvv74e"

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_basic_connectivity():
    """Test basic HTTP connectivity to CalDAV server."""
    print("=" * 60)
    print("1. Testing basic connectivity...")
    
    try:
        client = caldav.DAVClient(
            CALDAV_URL,
            username=USERNAME,
            password=PASSWORD,
            ssl_verify_cert=True,
            timeout=30,
        )
        
        # Test basic HTTP request
        response = client.request(CALDAV_URL)
        print(f"✅ Basic HTTP connectivity: SUCCESS")
        print(f"   Response status: {response.status}")
        return client
        
    except Exception as e:
        print(f"❌ Basic connectivity failed: {e}")
        return None

def test_principal_discovery(client):
    """Test principal discovery (this often fails with 400 on calendar.mail.ru)."""
    print("\n" + "=" * 60)
    print("2. Testing principal discovery...")
    
    try:
        principal = client.principal()
        print(f"✅ Principal discovery: SUCCESS")
        print(f"   Principal URL: {principal.url}")
        return principal
        
    except PropfindError as e:
        print(f"⚠️  Principal discovery failed with PropfindError: {e}")
        if "400" in str(e):
            print("   This is expected with calendar.mail.ru - 400 Bad Request")
        return None
        
    except Exception as e:
        print(f"❌ Principal discovery failed: {e}")
        return None

def test_calendar_home_set_discovery(client):
    """Test alternative calendar discovery without principal."""
    print("\n" + "=" * 60)
    print("3. Testing calendar home set discovery...")
    
    try:
        # Try to discover calendar home set directly
        # This is what the integration should do when principal() fails
        
        # Try common CalDAV paths for calendar.mail.ru
        potential_paths = [
            f"{CALDAV_URL}/dav/{USERNAME}/calendar/",
            f"{CALDAV_URL}/caldav/{USERNAME}/",
            f"{CALDAV_URL}/dav/{USERNAME}/",
            f"{CALDAV_URL}/calendar/dav/{USERNAME}/",
        ]
        
        for path in potential_paths:
            try:
                print(f"   Trying path: {path}")
                calendar_home = caldav.CalendarSet(client, url=path)
                calendars = calendar_home.calendars()
                if calendars:
                    print(f"✅ Found calendars via path: {path}")
                    print(f"   Number of calendars: {len(calendars)}")
                    return calendars
                    
            except Exception as e:
                print(f"   Path failed: {e}")
                continue
                
        print("❌ No working calendar paths found")
        return []
        
    except Exception as e:
        print(f"❌ Calendar home set discovery failed: {e}")
        return []

def test_calendar_enumeration(calendars):
    """Test individual calendar properties and capabilities."""
    print("\n" + "=" * 60)
    print("4. Testing calendar enumeration...")
    
    if not calendars:
        print("❌ No calendars to test")
        return []
        
    valid_calendars = []
    
    for i, calendar in enumerate(calendars):
        try:
            print(f"\n   Calendar {i+1}:")
            print(f"     URL: {calendar.url}")
            
            # Try to get calendar name
            try:
                name = calendar.name
                print(f"     Name: {name}")
            except Exception as e:
                print(f"     Name: Could not retrieve ({e})")
                name = f"Calendar {i+1}"
            
            # Try to get supported components
            try:
                supported_components = calendar.get_supported_components()
                print(f"     Supported components: {supported_components}")
            except Exception as e:
                print(f"     Supported components: Could not retrieve ({e})")
                supported_components = []
            
            # Check if calendar supports events or todos
            supports_events = 'VEVENT' in supported_components if supported_components else True
            supports_todos = 'VTODO' in supported_components if supported_components else True
            
            print(f"     Supports events: {supports_events}")
            print(f"     Supports todos: {supports_todos}")
            
            if supports_events or supports_todos:
                valid_calendars.append({
                    'calendar': calendar,
                    'name': name,
                    'supports_events': supports_events,
                    'supports_todos': supports_todos
                })
                print(f"     ✅ Calendar is valid for integration")
            else:
                print(f"     ❌ Calendar doesn't support events or todos")
                
        except Exception as e:
            print(f"     ❌ Error processing calendar: {e}")
            
    print(f"\n   Total valid calendars: {len(valid_calendars)}")
    return valid_calendars

def test_event_search(valid_calendars):
    """Test searching for events in valid calendars."""
    print("\n" + "=" * 60)
    print("5. Testing event search...")
    
    if not valid_calendars:
        print("❌ No valid calendars to search")
        return
    
    # Search for events in the next 30 days
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    for cal_info in valid_calendars:
        calendar = cal_info['calendar']
        name = cal_info['name']
        
        print(f"\n   Searching calendar: {name}")
        
        if cal_info['supports_events']:
            try:
                events = calendar.search(
                    start=start_date,
                    end=end_date,
                    event=True,
                    expand=True,
                )
                print(f"     ✅ Found {len(events)} events")
                
                # Show first few events
                for i, event in enumerate(events[:3]):
                    try:
                        if hasattr(event.instance, 'vevent'):
                            vevent = event.instance.vevent
                            summary = getattr(vevent, 'summary', 'No title')
                            dtstart = getattr(vevent, 'dtstart', 'No start time')
                            print(f"       Event {i+1}: {summary} ({dtstart})")
                    except Exception as e:
                        print(f"       Event {i+1}: Error reading event details ({e})")
                        
            except Exception as e:
                print(f"     ❌ Event search failed: {e}")
        
        if cal_info['supports_todos']:
            try:
                todos = calendar.search(
                    start=start_date,
                    end=end_date,
                    todo=True,
                    expand=True,
                )
                print(f"     ✅ Found {len(todos)} todos")
                
                # Show first few todos
                for i, todo in enumerate(todos[:3]):
                    try:
                        if hasattr(todo.instance, 'vtodo'):
                            vtodo = todo.instance.vtodo
                            summary = getattr(vtodo, 'summary', 'No title')
                            print(f"       Todo {i+1}: {summary}")
                    except Exception as e:
                        print(f"       Todo {i+1}: Error reading todo details ({e})")
                        
            except Exception as e:
                print(f"     ❌ Todo search failed: {e}")

def test_integration_api():
    """Test the integration's API functions."""
    print("\n" + "=" * 60)
    print("6. Testing integration API functions...")
    
    # Add custom component path
    sys.path.insert(0, 'custom_components/caldav_custom')
    
    try:
        from api import async_get_calendars
        print("✅ Successfully imported integration API")
        
        # This would need async context to test properly
        print("   (Async API testing would require integration context)")
        
    except Exception as e:
        print(f"❌ Failed to import integration API: {e}")

def main():
    """Run all CalDAV tests."""
    print("CalDAV Integration Debug Test")
    print("Testing with calendar.mail.ru")
    print(f"URL: {CALDAV_URL}")
    print(f"Username: {USERNAME}")
    print("=" * 60)
    
    # Test 1: Basic connectivity
    client = test_basic_connectivity()
    if not client:
        print("\n❌ Cannot proceed - basic connectivity failed")
        return
    
    # Test 2: Principal discovery (expected to fail)
    principal = test_principal_discovery(client)
    
    # Test 3: Alternative calendar discovery
    calendars = test_calendar_home_set_discovery(client)
    
    # Test 4: Calendar enumeration
    valid_calendars = test_calendar_enumeration(calendars)
    
    # Test 5: Event/todo search
    test_event_search(valid_calendars)
    
    # Test 6: Integration API
    test_integration_api()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"- Valid calendars found: {len(valid_calendars) if 'valid_calendars' in locals() else 0}")
    
    if valid_calendars:
        print("✅ CalDAV server is functional - investigate why integration creates no entities")
        print("\nNext steps:")
        print("1. Check integration's async_get_calendars() function")
        print("2. Verify calendar filtering logic")
        print("3. Check entity creation in calendar.py and todo.py")
    else:
        print("❌ No functional calendars found - server may not be compatible")

if __name__ == "__main__":
    main()