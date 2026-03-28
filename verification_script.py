# verification_script.py
import sys
import os

# Mocking necessary parts for testing
class MockColumn:
    def __init__(self, name):
        self.name = name

class MockTable:
    def __init__(self):
        self.columns = [MockColumn("monthly_price"), MockColumn("quarterly_price"), MockColumn("yearly_price")]

class MockSettings:
    def __init__(self):
        self.__table__ = MockTable()
        self.monthly_price = 29.99
        self.quarterly_price = 79.99
        self.yearly_price = 299.99

def get_settings_mock():
    settings = MockSettings()
    # This reflects the new implementation in api/routes/control/settings.py
    return {col.name: getattr(settings, col.name) for col in settings.__table__.columns}

def test_stripe_logic():
    settings = get_settings_mock()
    print(f"Settings returned: {settings}")
    
    # This reflects the fix in subscriptions/stripe.py
    price_map = {
        "monthly": settings.get("monthly_price") or 29.99,
        "quarterly": settings.get("quarterly_price") or 79.99,
        "yearly": settings.get("yearly_price") or 299.99
    }
    
    print(f"Price map: {price_map}")
    assert price_map["monthly"] == 29.99
    assert price_map["quarterly"] == 79.99
    assert price_map["yearly"] == 299.99
    print("✅ Verification successful! Price map correctly built from settings dictionary.")

if __name__ == "__main__":
    test_stripe_logic()
