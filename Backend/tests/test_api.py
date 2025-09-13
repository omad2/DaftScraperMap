import requests
import json
import time
from typing import Dict, Any

class APITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_health_check(self) -> bool:
        """Test health check endpoint"""
        print("Testing health check...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Health check passed: {data['status']}")
                return True
            else:
                print(f"✗ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Health check error: {str(e)}")
            return False
    
    def test_root_endpoint(self) -> bool:
        """Test root endpoint"""
        print("Testing root endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Root endpoint passed: {data['message']}")
                return True
            else:
                print(f"✗ Root endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Root endpoint error: {str(e)}")
            return False
    
    def test_get_properties(self) -> bool:
        """Test get properties endpoint"""
        print("Testing get properties...")
        try:
            response = self.session.get(f"{self.base_url}/properties?limit=5")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Get properties passed: {data['total_count']} total properties")
                return True
            else:
                print(f"✗ Get properties failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Get properties error: {str(e)}")
            return False
    
    def test_get_statistics(self) -> bool:
        """Test statistics endpoint"""
        print("Testing statistics...")
        try:
            response = self.session.get(f"{self.base_url}/statistics")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Statistics passed: {data['total_properties']} total properties")
                return True
            else:
                print(f"✗ Statistics failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Statistics error: {str(e)}")
            return False
    
    def test_scraping_validation(self) -> bool:
        """Test scraping endpoint validation"""
        print("Testing scraping validation...")
        try:
            # Test invalid request
            invalid_request = {
                "listing_type": "invalid_type",
                "location": "invalid_location"
            }
            response = self.session.post(
                f"{self.base_url}/scrape",
                json=invalid_request
            )
            if response.status_code == 422:  # Validation error
                print("✓ Scraping validation passed: correctly rejected invalid request")
                return True
            else:
                print(f"✗ Scraping validation failed: expected 422, got {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Scraping validation error: {str(e)}")
            return False
    
    def test_property_filters(self) -> bool:
        """Test property filtering"""
        print("Testing property filters...")
        try:
            # Test with filters
            params = {
                "listing_type": "rent",
                "min_price": 1000,
                "max_price": 3000,
                "min_bedrooms": 1,
                "limit": 3
            }
            response = self.session.get(f"{self.base_url}/properties", params=params)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Property filters passed: {len(data['properties'])} filtered properties")
                return True
            else:
                print(f"✗ Property filters failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Property filters error: {str(e)}")
            return False
    
    def test_invalid_property_id(self) -> bool:
        """Test invalid property ID"""
        print("Testing invalid property ID...")
        try:
            response = self.session.get(f"{self.base_url}/properties/999999")
            if response.status_code == 404:
                print("✓ Invalid property ID test passed: correctly returned 404")
                return True
            else:
                print(f"✗ Invalid property ID test failed: expected 404, got {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Invalid property ID test error: {str(e)}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        print("=" * 50)
        print("DublinMap API Test Suite")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Root Endpoint", self.test_root_endpoint),
            ("Get Properties", self.test_get_properties),
            ("Statistics", self.test_get_statistics),
            ("Scraping Validation", self.test_scraping_validation),
            ("Property Filters", self.test_property_filters),
            ("Invalid Property ID", self.test_invalid_property_id),
        ]
        
        results = {}
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{test_name}:")
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    passed += 1
            except Exception as e:
                print(f"✗ {test_name} failed with exception: {str(e)}")
                results[test_name] = False
        
        print("\n" + "=" * 50)
        print(f"Test Results: {passed}/{total} tests passed")
        print("=" * 50)
        
        for test_name, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{test_name}: {status}")
        
        return results

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test DublinMap API")
    parser.add_argument(
        "--url", 
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--wait", 
        type=int, 
        default=0,
        help="Wait time in seconds before starting tests"
    )
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"Waiting {args.wait} seconds before starting tests...")
        time.sleep(args.wait)
    
    tester = APITester(args.url)
    results = tester.run_all_tests()
    
    # Exit with error code if any tests failed
    if not all(results.values()):
        exit(1)

if __name__ == "__main__":
    main()
