
import sys
import os
import inspect

# Add project root to path
sys.path.append(os.getcwd())

def test_crs_create_schema():
    print("Testing CRSCreate schema...")
    try:
        from app.schemas.crs import CRSCreate
        # Try creating an instance with pattern
        obj = CRSCreate(
            project_id=1, 
            content="test", 
            pattern="agile_user_stories"
        )
        if getattr(obj, 'pattern', None) == "agile_user_stories":
            print("✅ CRSCreate accepts 'pattern' field correctly.")
            return True
        else:
            print(f"❌ CRSCreate 'pattern' field is {getattr(obj, 'pattern', 'MISSING')}, expected 'agile_user_stories'")
            return False
    except ImportError as e:
        print(f"❌ Could not import CRSCreate: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing CRSCreate: {e}")
        return False

def test_persist_crs_document_signature():
    print("\nTesting persist_crs_document signature...")
    try:
        from app.services.crs_service import persist_crs_document
        sig = inspect.signature(persist_crs_document)
        if 'pattern' in sig.parameters:
            print("✅ persist_crs_document accepts 'pattern' argument.")
            return True
        else:
            print("❌ persist_crs_document MISSING 'pattern' argument.")
            return False
    except ImportError as e:
        print(f"❌ Could not import persist_crs_document: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing persist_crs_document: {e}")
        return False

if __name__ == "__main__":
    schema_ok = test_crs_create_schema()
    sig_ok = test_persist_crs_document_signature()
    
    if schema_ok and sig_ok:
        print("\n✅ All verification checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Checks failed!")
        sys.exit(1)
