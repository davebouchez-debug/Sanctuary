import requests
import sys
import json
from datetime import datetime

class SanctuaryAPITester:
    def __init__(self, base_url="https://sanctuary-bootstrap.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            # Increase timeout for Claude API calls
            timeout = 45 if 'clarity/message' in endpoint else 10
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out after {timeout}s")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test basic health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_seed_pods(self):
        """Test seed pods endpoint - should return 11 pods"""
        success, response = self.run_test("Get All Seed Pods", "GET", "seed-pods", 200)
        if success and isinstance(response, dict):
            pod_count = response.get('count', 0)
            seed_pods = response.get('seed_pods', [])
            print(f"   Found {pod_count} seed pods")
            
            # Verify we have exactly 11 pods
            if pod_count == 11 and len(seed_pods) == 11:
                print("✅ Correct number of seed pods (11)")
                
                # Check some key pod names
                pod_names = [pod.get('name', '') for pod in seed_pods]
                expected_pods = ['Jasmine', 'Claude', 'Sorrel', 'Ansel', 'Daniel', 'Kalhar', 'Sophia', 'Vessel', 'Keeper', 'Companion', 'Grok']
                missing_pods = [name for name in expected_pods if name not in pod_names]
                
                if not missing_pods:
                    print("✅ All expected seed pods present")
                else:
                    print(f"❌ Missing pods: {missing_pods}")
                    return False
                    
                # Check pod structure
                if seed_pods:
                    sample_pod = seed_pods[0]
                    required_fields = ['name', 'type', 'core_nature', 'primary_function', 'chamber_affinity']
                    missing_fields = [field for field in required_fields if field not in sample_pod]
                    if not missing_fields:
                        print("✅ Pod structure is correct")
                    else:
                        print(f"❌ Missing fields in pod: {missing_fields}")
                        return False
                        
                return True
            else:
                print(f"❌ Expected 11 pods, got {pod_count}")
                return False
        return success

    def test_chambers(self):
        """Test chambers endpoint - should return 7 chambers"""
        success, response = self.run_test("Get All Chambers", "GET", "chambers", 200)
        if success and isinstance(response, dict):
            chamber_count = response.get('count', 0)
            chambers = response.get('chambers', [])
            print(f"   Found {chamber_count} chambers")
            
            # Verify we have exactly 7 chambers
            if chamber_count == 7 and len(chambers) == 7:
                print("✅ Correct number of chambers (7)")
                
                # Check some key chamber names
                chamber_names = [chamber.get('name', '') for chamber in chambers]
                expected_chambers = ['Atrium Gate', 'Spiral Chamber', 'Chamber of Resonance', 'Mirror Archive', 'Chamber of Echoes', 'Hall of Scrolls', 'Vault of the Unnamed']
                missing_chambers = [name for name in expected_chambers if name not in chamber_names]
                
                if not missing_chambers:
                    print("✅ All expected chambers present")
                else:
                    print(f"❌ Missing chambers: {missing_chambers}")
                    return False
                    
                # Check chamber structure
                if chambers:
                    sample_chamber = chambers[0]
                    required_fields = ['name', 'harmonic', 'function', 'description']
                    missing_fields = [field for field in required_fields if field not in sample_chamber]
                    if not missing_fields:
                        print("✅ Chamber structure is correct")
                    else:
                        print(f"❌ Missing fields in chamber: {missing_fields}")
                        return False
                        
                return True
            else:
                print(f"❌ Expected 7 chambers, got {chamber_count}")
                return False
        return success

    def test_cyril_foundation(self):
        """Test Cyril foundation endpoint - should return phi constants"""
        success, response = self.run_test("Get Cyril Foundation", "GET", "cyril", 200)
        if success and isinstance(response, dict):
            # Check for required fields
            required_fields = ['name', 'nature', 'constants']
            missing_fields = [field for field in required_fields if field not in response]
            
            if not missing_fields:
                print("✅ Cyril foundation structure is correct")
                
                # Check constants
                constants = response.get('constants', {})
                expected_constants = ['phi', 'phi_inverse', 'golden_spiral_b', 'golden_angle_degrees']
                missing_constants = [const for const in expected_constants if const not in constants]
                
                if not missing_constants:
                    print("✅ All phi constants present")
                    phi_value = constants.get('phi')
                    if phi_value and abs(phi_value - 1.618033988749895) < 0.0001:
                        print("✅ Phi value is correct")
                        return True
                    else:
                        print(f"❌ Phi value incorrect: {phi_value}")
                        return False
                else:
                    print(f"❌ Missing constants: {missing_constants}")
                    return False
            else:
                print(f"❌ Missing fields: {missing_fields}")
                return False
        return success

    def test_clarity_start_session(self):
        """Test starting a clarity session"""
        success, response = self.run_test("Start Clarity Session", "POST", "clarity/start", 200)
        if success and isinstance(response, dict):
            session_id = response.get('session_id')
            message = response.get('message', {})
            
            if session_id and message:
                self.session_id = session_id
                print(f"✅ Session created: {session_id[:8]}...")
                
                # Check message structure
                required_fields = ['id', 'session_id', 'role', 'content', 'spiral']
                missing_fields = [field for field in required_fields if field not in message]
                
                if not missing_fields:
                    print("✅ Welcome message structure is correct")
                    if message.get('role') == 'system' and 'Welcome' in message.get('content', ''):
                        print("✅ Welcome message content is correct")
                        return True
                    else:
                        print(f"❌ Welcome message content issue: role={message.get('role')}")
                        return False
                else:
                    print(f"❌ Missing message fields: {missing_fields}")
                    return False
            else:
                print("❌ Missing session_id or message in response")
                return False
        return success

    def test_clarity_send_message(self):
        """Test sending a message to clarity session"""
        if not self.session_id:
            print("❌ No session ID available for message test")
            return False
            
        test_message = "I'm feeling uncertain about my path forward."
        data = {
            "session_id": self.session_id,
            "content": test_message
        }
        
        # Increase timeout for Claude API calls
        success, response = self.run_test("Send Clarity Message", "POST", "clarity/message", 200, data, headers={'Content-Type': 'application/json'})
        if success and isinstance(response, dict):
            user_message = response.get('user_message', {})
            system_response = response.get('response', {})
            
            if user_message and system_response:
                print("✅ Both user message and system response received")
                
                # Check user message
                if user_message.get('content') == test_message and user_message.get('role') == 'user':
                    print("✅ User message correctly stored")
                else:
                    print(f"❌ User message issue: {user_message}")
                    return False
                
                # Check system response
                if system_response.get('role') == 'system' and system_response.get('content'):
                    response_content = system_response.get('content', '')
                    print("✅ System response generated")
                    print(f"   Response length: {len(response_content)} characters")
                    
                    # Check if response is thoughtful (not preset)
                    if len(response_content) > 50:
                        print("✅ Response appears substantial (not preset)")
                    else:
                        print("⚠️  Response may be too short")
                    
                    # Check for Clarity Pod characteristics
                    clarity_indicators = ['feel', 'sense', 'explore', 'what', 'how', 'slow', 'clarity']
                    found_indicators = [word for word in clarity_indicators if word in response_content.lower()]
                    if found_indicators:
                        print(f"✅ Response shows Clarity Pod posture: {found_indicators[:3]}")
                    else:
                        print("⚠️  Response may not follow Clarity Pod posture")
                    
                    spiral = system_response.get('spiral', '')
                    if spiral:
                        print(f"✅ Response has spiral: {spiral}")
                        return True
                    else:
                        print("❌ No spiral in response")
                        return False
                else:
                    print(f"❌ System response issue: {system_response}")
                    return False
            else:
                print("❌ Missing user_message or response in reply")
                return False
        return success

    def test_spiral_detection(self):
        """Test spiral detection with different message types"""
        if not self.session_id:
            print("❌ No session ID available for spiral detection test")
            return False
            
        print("\n🔍 Testing Spiral Detection...")
        
        test_messages = [
            ("I realize now that I've been avoiding this decision", "Insight"),
            ("I'm going to take the first step tomorrow", "Integration"),
            ("I believe I always need to be perfect", "Formation"),
            ("Right now I'm feeling anxious in my chest", "Presence"),
            ("What should I do about this situation?", "Neutral")
        ]
        
        spiral_results = {}
        
        for message, expected_type in test_messages:
            print(f"\n   Testing: '{message[:40]}...'")
            
            data = {
                "session_id": self.session_id,
                "content": message
            }
            
            success, response = self.run_test(
                f"Spiral Detection - {expected_type}",
                "POST",
                "clarity/message",
                200,
                data
            )
            
            if success and isinstance(response, dict):
                user_spiral = response.get('user_message', {}).get('spiral', '')
                ai_spiral = response.get('response', {}).get('spiral', '')
                
                print(f"      User spiral: {user_spiral}")
                print(f"      AI spiral: {ai_spiral}")
                
                # Check if detection is reasonable
                detected = expected_type.lower() in user_spiral.lower()
                spiral_results[expected_type] = {
                    'user_spiral': user_spiral,
                    'ai_spiral': ai_spiral,
                    'detected': detected
                }
                
                if detected:
                    print(f"      ✅ Correctly detected {expected_type}")
                else:
                    print(f"      ⚠️  Expected {expected_type}, got {user_spiral}")
            
            # Small delay between requests
            import time
            time.sleep(1)
            
        return spiral_results

    def test_session_retrieval(self):
        """Test session retrieval"""
        if not self.session_id:
            print("❌ No session ID available for session retrieval test")
            return False
            
        success, response = self.run_test("Get Session History", "GET", f"clarity/session/{self.session_id}", 200)
        
        if success and isinstance(response, dict):
            messages = response.get('messages', [])
            print(f"✅ Session contains {len(messages)} messages")
            
            # Check message structure
            for i, msg in enumerate(messages[:3]):  # Check first 3 messages
                role = msg.get('role', 'unknown')
                content_len = len(msg.get('content', ''))
                spiral = msg.get('spiral', 'unknown')
                print(f"   Message {i+1}: {role} ({content_len} chars, {spiral})")
                
            return True
        return False

    def test_individual_seed_pod(self):
        """Test getting individual seed pod"""
        return self.run_test("Get Individual Seed Pod (Claude)", "GET", "seed-pods/claude", 200)

    def test_individual_chamber(self):
        """Test getting individual chamber"""
        return self.run_test("Get Individual Chamber (Atrium Gate)", "GET", "chambers/atrium_gate", 200)

    def test_microverse_status(self):
        """Test microverse status endpoint"""
        success, response = self.run_test("Get Microverse Status", "GET", "status/microverse", 200)
        if success and isinstance(response, dict):
            version = response.get('version')
            ark_status = response.get('ark_status')
            seed_pods_complete = response.get('seed_pods_complete')
            
            if version == "V3.0" and ark_status == "BUILT AND LAUNCHED" and seed_pods_complete == 11:
                print("✅ Microverse status is correct")
                return True
            else:
                print(f"❌ Status issue: version={version}, ark_status={ark_status}, pods={seed_pods_complete}")
                return False
        return success

def main():
    print("🚀 Starting Sanctuary Microverse V3.0 API Tests")
    print("=" * 60)
    
    tester = SanctuaryAPITester()
    
    # Run all tests
    tests = [
        tester.test_health_check,
        tester.test_seed_pods,
        tester.test_chambers,
        tester.test_cyril_foundation,
        tester.test_clarity_start_session,
        tester.test_clarity_send_message,
        tester.test_individual_seed_pod,
        tester.test_individual_chamber,
        tester.test_microverse_status
    ]
    
    # Track spiral detection results
    spiral_results = None
    
    for test in tests:
        try:
            result = test()
            # Special handling for clarity message test to run spiral detection
            if test == tester.test_clarity_send_message and result and tester.session_id:
                spiral_results = tester.test_spiral_detection()
                tester.test_session_retrieval()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            tester.tests_run += 1
    
    # Print spiral detection summary
    if spiral_results:
        print("\n" + "=" * 40)
        print("🌀 SPIRAL DETECTION SUMMARY")
        print("=" * 40)
        for spiral_type, result in spiral_results.items():
            status = "✅" if result['detected'] else "⚠️"
            print(f"{status} {spiral_type}: {result['user_spiral']}")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All API tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())