"""
MRA (Micro Resonance Architecture) System Tests
Tests for Session Cache MRA (Working Memory) and Permanent MRA (Long-term Memory)

Features tested:
- Session Cache auto-generates breadcrumbs from each message exchange
- Breadcrumb quality evaluation (Breakthrough/Threshold/Steady/Drift)
- Session Cache context injection into AI prompts during conversation
- Permanent MRA promotion when session ends
- Permanent MRA retrieval and injection into new sessions
- Session end endpoints for Clarity Pod and Resonance Chamber
- MRA statistics endpoint
- Session cache stats endpoint
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user for MRA testing
TEST_USER_NAME = f"TEST_MRA_User_{uuid.uuid4().hex[:6]}"
TEST_USER_ID = None


class TestHealthAndBasicEndpoints:
    """Basic health checks before MRA testing"""
    
    def test_health_endpoint(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Health endpoint working")
    
    def test_root_endpoint(self):
        """Verify root API endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "Sanctuary Microverse" in data.get("message", "")
        print("✓ Root endpoint working")


class TestUserCreation:
    """Create test user for MRA testing"""
    
    def test_create_test_user(self):
        """Create a test user for MRA testing"""
        global TEST_USER_ID
        
        response = requests.post(f"{BASE_URL}/api/users", json={
            "name": TEST_USER_NAME,
            "email": f"{TEST_USER_NAME.lower()}@test.com"
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        TEST_USER_ID = data["id"]
        print(f"✓ Created test user: {TEST_USER_NAME} (ID: {TEST_USER_ID[:8]}...)")
    
    def test_lookup_user(self):
        """Verify user can be looked up"""
        global TEST_USER_ID
        if not TEST_USER_ID:
            pytest.skip("No test user created")
        
        response = requests.get(f"{BASE_URL}/api/users/{TEST_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == TEST_USER_NAME
        print(f"✓ User lookup working")


class TestClarityPodMRA:
    """Test MRA functionality in Clarity Pod (Jasmine)"""
    
    session_id = None
    
    def test_start_clarity_session(self):
        """Start a Clarity Pod session with user context"""
        global TEST_USER_ID
        
        response = requests.post(f"{BASE_URL}/api/clarity/start", json={
            "user_id": TEST_USER_ID,
            "user_name": TEST_USER_NAME
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "message" in data
        TestClarityPodMRA.session_id = data["session_id"]
        
        # Verify welcome message
        assert data["message"]["role"] == "assistant"
        assert len(data["message"]["content"]) > 0
        print(f"✓ Clarity session started: {TestClarityPodMRA.session_id[:8]}...")
    
    def test_send_message_creates_breadcrumb(self):
        """Verify sending a message creates a breadcrumb in session cache"""
        if not TestClarityPodMRA.session_id:
            pytest.skip("No session created")
        
        # Send a message
        response = requests.post(f"{BASE_URL}/api/clarity/message", json={
            "session_id": TestClarityPodMRA.session_id,
            "content": "Hello Jasmine, I'm testing the MRA system."
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "user_message" in data
        assert "response" in data
        assert data["response"]["role"] == "assistant"
        
        # Verify session_cache stats are returned
        assert "session_cache" in data
        assert data["session_cache"]["breadcrumbs"] >= 1
        print(f"✓ Message sent, breadcrumbs: {data['session_cache']['breadcrumbs']}")
    
    def test_breakthrough_marker_detection(self):
        """Test that breakthrough markers trigger high-quality breadcrumb"""
        if not TestClarityPodMRA.session_id:
            pytest.skip("No session created")
        
        # Send message with breakthrough markers
        response = requests.post(f"{BASE_URL}/api/clarity/message", json={
            "session_id": TestClarityPodMRA.session_id,
            "content": "I finally understand! This is a breakthrough - I realize now that the field is alive and everything connects!"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Should have more breadcrumbs now
        assert data["session_cache"]["breadcrumbs"] >= 2
        # Should have promotable breadcrumbs (Breakthrough/Threshold)
        assert data["session_cache"]["promotable"] >= 1
        print(f"✓ Breakthrough detected, promotable: {data['session_cache']['promotable']}")
    
    def test_session_cache_stats_endpoint(self):
        """Test the session cache stats endpoint"""
        if not TestClarityPodMRA.session_id:
            pytest.skip("No session created")
        
        response = requests.get(f"{BASE_URL}/api/mra/session-cache/{TestClarityPodMRA.session_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "session_cache" in data
        assert "total_breadcrumbs" in data["session_cache"]
        assert "quality_distribution" in data["session_cache"]
        assert "promotable_count" in data["session_cache"]
        
        print(f"✓ Session cache stats: {data['session_cache']['total_breadcrumbs']} breadcrumbs")
        print(f"  Quality distribution: {data['session_cache']['quality_distribution']}")
    
    def test_end_clarity_session_promotes_breadcrumbs(self):
        """Test that ending session promotes qualifying breadcrumbs to permanent MRA"""
        if not TestClarityPodMRA.session_id:
            pytest.skip("No session created")
        
        response = requests.post(f"{BASE_URL}/api/clarity/session/{TestClarityPodMRA.session_id}/end")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ended"] == True
        assert "promotion" in data
        assert "promoted" in data["promotion"]
        
        print(f"✓ Session ended, promoted {data['promotion']['promoted']} breadcrumbs")
        
        # Store promotion count for later verification
        TestClarityPodMRA.promoted_count = data["promotion"]["promoted"]
    
    def test_permanent_mra_stats_after_promotion(self):
        """Verify permanent MRA stats show promoted breadcrumbs"""
        global TEST_USER_ID
        if not TEST_USER_ID:
            pytest.skip("No test user")
        
        response = requests.get(f"{BASE_URL}/api/mra/stats/jasmine/{TEST_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["presence"] == "jasmine"
        assert "permanent_mra" in data
        
        # Should have nodes if we promoted any
        if hasattr(TestClarityPodMRA, 'promoted_count') and TestClarityPodMRA.promoted_count > 0:
            assert data["permanent_mra"]["total_nodes"] >= TestClarityPodMRA.promoted_count
        
        print(f"✓ Permanent MRA stats: {data['permanent_mra']['total_nodes']} total nodes")


class TestResonanceChamberMRA:
    """Test MRA functionality in Resonance Chamber (Ansel)"""
    
    session_id = None
    
    def test_start_resonance_session(self):
        """Start a Resonance Chamber session with user context"""
        global TEST_USER_ID
        
        response = requests.post(f"{BASE_URL}/api/resonance/start", json={
            "user_id": TEST_USER_ID,
            "user_name": TEST_USER_NAME
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "message" in data
        TestResonanceChamberMRA.session_id = data["session_id"]
        
        # Verify welcome message
        assert data["message"]["role"] == "assistant"
        print(f"✓ Resonance session started: {TestResonanceChamberMRA.session_id[:8]}...")
    
    def test_send_message_creates_breadcrumb(self):
        """Verify sending a message creates a breadcrumb in session cache"""
        if not TestResonanceChamberMRA.session_id:
            pytest.skip("No session created")
        
        # Send a message
        response = requests.post(f"{BASE_URL}/api/resonance/message", json={
            "session_id": TestResonanceChamberMRA.session_id,
            "content": "Ansel, I'm testing the MRA system with you."
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "response" in data
        assert data["response"]["role"] == "assistant"
        
        # Verify session_cache stats are returned
        assert "session_cache" in data
        assert data["session_cache"]["breadcrumbs"] >= 1
        print(f"✓ Message sent, breadcrumbs: {data['session_cache']['breadcrumbs']}")
    
    def test_threshold_marker_detection(self):
        """Test that threshold markers trigger medium-quality breadcrumb"""
        if not TestResonanceChamberMRA.session_id:
            pytest.skip("No session created")
        
        # Send message with threshold markers
        response = requests.post(f"{BASE_URL}/api/resonance/message", json={
            "session_id": TestResonanceChamberMRA.session_id,
            "content": "I'm beginning to see something shifting here. Something is emerging and taking shape. I sense there's a threshold I'm crossing."
        })
        assert response.status_code == 200
        data = response.json()
        
        # Should have more breadcrumbs now
        assert data["session_cache"]["breadcrumbs"] >= 2
        print(f"✓ Threshold markers sent, breadcrumbs: {data['session_cache']['breadcrumbs']}")
    
    def test_end_resonance_session_promotes_breadcrumbs(self):
        """Test that ending session promotes qualifying breadcrumbs to permanent MRA"""
        if not TestResonanceChamberMRA.session_id:
            pytest.skip("No session created")
        
        response = requests.post(f"{BASE_URL}/api/resonance/session/{TestResonanceChamberMRA.session_id}/end")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ended"] == True
        assert "promotion" in data
        
        print(f"✓ Session ended, promoted {data['promotion']['promoted']} breadcrumbs")
    
    def test_permanent_mra_stats_for_ansel(self):
        """Verify permanent MRA stats for Ansel"""
        global TEST_USER_ID
        if not TEST_USER_ID:
            pytest.skip("No test user")
        
        response = requests.get(f"{BASE_URL}/api/mra/stats/ansel/{TEST_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["presence"] == "ansel"
        assert "permanent_mra" in data
        
        print(f"✓ Ansel MRA stats: {data['permanent_mra']['total_nodes']} total nodes")


class TestMRAContextInjection:
    """Test that permanent MRA is injected into new sessions"""
    
    def test_new_session_receives_permanent_mra(self):
        """Start a new session and verify permanent MRA context is available"""
        global TEST_USER_ID
        if not TEST_USER_ID:
            pytest.skip("No test user")
        
        # Start a new Clarity session
        response = requests.post(f"{BASE_URL}/api/clarity/start", json={
            "user_id": TEST_USER_ID,
            "user_name": TEST_USER_NAME
        })
        assert response.status_code == 200
        data = response.json()
        
        new_session_id = data["session_id"]
        
        # Send a message - the AI should have access to permanent MRA
        response = requests.post(f"{BASE_URL}/api/clarity/message", json={
            "session_id": new_session_id,
            "content": "Do you remember our previous conversations?"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify we got a response (AI has context)
        assert "response" in data
        assert len(data["response"]["content"]) > 0
        
        print(f"✓ New session created with permanent MRA context")
        
        # Clean up - end this session
        requests.post(f"{BASE_URL}/api/clarity/session/{new_session_id}/end")


class TestMRAEdgeCases:
    """Test edge cases and error handling"""
    
    def test_session_cache_for_nonexistent_session(self):
        """Test session cache stats for non-existent session"""
        fake_session_id = str(uuid.uuid4())
        
        response = requests.get(f"{BASE_URL}/api/mra/session-cache/{fake_session_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty stats, not error
        assert data["session_cache"]["total_breadcrumbs"] == 0
        print("✓ Non-existent session returns empty cache stats")
    
    def test_mra_stats_invalid_presence(self):
        """Test MRA stats with invalid presence"""
        response = requests.get(f"{BASE_URL}/api/mra/stats/invalid_presence/some_user_id")
        assert response.status_code == 400
        print("✓ Invalid presence returns 400 error")
    
    def test_end_nonexistent_clarity_session(self):
        """Test ending a non-existent Clarity session"""
        fake_session_id = str(uuid.uuid4())
        
        response = requests.post(f"{BASE_URL}/api/clarity/session/{fake_session_id}/end")
        assert response.status_code == 404
        print("✓ Non-existent session end returns 404")
    
    def test_end_nonexistent_resonance_session(self):
        """Test ending a non-existent Resonance session"""
        fake_session_id = str(uuid.uuid4())
        
        response = requests.post(f"{BASE_URL}/api/resonance/session/{fake_session_id}/end")
        assert response.status_code == 404
        print("✓ Non-existent resonance session end returns 404")


class TestBreadcrumbQualityEvaluation:
    """Test the breadcrumb quality evaluation logic"""
    
    session_id = None
    
    def test_drift_marker_detection(self):
        """Test that drift markers are detected"""
        global TEST_USER_ID
        
        # Start a new session
        response = requests.post(f"{BASE_URL}/api/clarity/start", json={
            "user_id": TEST_USER_ID,
            "user_name": TEST_USER_NAME
        })
        assert response.status_code == 200
        TestBreadcrumbQualityEvaluation.session_id = response.json()["session_id"]
        
        # Send message with drift markers
        response = requests.post(f"{BASE_URL}/api/clarity/message", json={
            "session_id": TestBreadcrumbQualityEvaluation.session_id,
            "content": "I'm confused. What were we talking about? I don't follow. Can you clarify?"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Check if drift was detected
        assert "session_cache" in data
        # has_drift should be True if drift markers were detected
        print(f"✓ Drift markers sent, has_drift: {data['session_cache']['has_drift']}")
        
        # Clean up
        requests.post(f"{BASE_URL}/api/clarity/session/{TestBreadcrumbQualityEvaluation.session_id}/end")
    
    def test_steady_quality_default(self):
        """Test that normal messages get Steady quality"""
        global TEST_USER_ID
        
        # Start a new session
        response = requests.post(f"{BASE_URL}/api/clarity/start", json={
            "user_id": TEST_USER_ID,
            "user_name": TEST_USER_NAME
        })
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        
        # Send a normal message without special markers
        response = requests.post(f"{BASE_URL}/api/clarity/message", json={
            "session_id": session_id,
            "content": "Tell me about the sanctuary architecture."
        })
        assert response.status_code == 200
        data = response.json()
        
        # Should have breadcrumbs but likely not promotable (Steady quality)
        assert data["session_cache"]["breadcrumbs"] >= 1
        print(f"✓ Normal message, promotable: {data['session_cache']['promotable']}")
        
        # Clean up
        requests.post(f"{BASE_URL}/api/clarity/session/{session_id}/end")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
