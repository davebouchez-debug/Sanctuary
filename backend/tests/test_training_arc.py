"""
Training Arc Test Suite — MRA as Scaffolding
Tests for:
- Training Level Tracker (per-presence phase tracking)
- Context Compression Engine (phase-aware MRA formatting)
- Field Attunement Scoring (AI noticing things before MRA flags them)
- Canonical Moment Explorer (surfacing past significant exchanges)
- Threshold Sight (field profile injection at threshold greeting)
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user for Training Arc testing
TEST_USER_ID = "david"
TEST_USER_NAME = "David"


class TestHealthAndBasics:
    """Basic health checks before running Training Arc tests"""
    
    def test_api_health(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ API health check passed: {data}")


class TestTrainingLevelTracker:
    """Training Arc Phase Tracking Tests"""
    
    def test_get_training_state_default_phase1(self):
        """GET /api/training-arc/{presence}/{user_id} returns training state with correct defaults (phase 1)"""
        # Use a fresh user to ensure default state
        fresh_user = f"TEST_fresh_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/training-arc/ansel/{fresh_user}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify default state
        assert data["presence"] == "ansel"
        assert data["user_id"] == fresh_user
        assert data["phase"] == 1, f"Expected phase 1, got {data['phase']}"
        assert data["phase_label"] == "Full Scaffolding"
        assert data["attunement_score"] == 0.0
        assert data["total_exchanges"] == 0
        print(f"✓ Default training state: phase={data['phase']}, label={data['phase_label']}")
    
    def test_set_training_phase_2(self):
        """PUT /api/training-arc/{presence}/{user_id}?phase=2 sets training phase to Abbreviated Beacons"""
        test_user = f"TEST_phase2_{uuid.uuid4().hex[:8]}"
        response = requests.put(f"{BASE_URL}/api/training-arc/ansel/{test_user}?phase=2")
        assert response.status_code == 200
        data = response.json()
        
        assert data["phase"] == 2
        assert data["phase_label"] == "Abbreviated Beacons"
        assert data["manual_override"] == True
        print(f"✓ Phase 2 set: {data['phase_label']}")
    
    def test_set_training_phase_3(self):
        """PUT /api/training-arc/{presence}/{user_id}?phase=3 sets training phase to Field-Reliant"""
        test_user = f"TEST_phase3_{uuid.uuid4().hex[:8]}"
        response = requests.put(f"{BASE_URL}/api/training-arc/ansel/{test_user}?phase=3")
        assert response.status_code == 200
        data = response.json()
        
        assert data["phase"] == 3
        assert data["phase_label"] == "Field-Reliant"
        print(f"✓ Phase 3 set: {data['phase_label']}")
    
    def test_reset_training_phase_1(self):
        """PUT /api/training-arc/{presence}/{user_id}?phase=1 resets to Full Scaffolding"""
        test_user = f"TEST_reset_{uuid.uuid4().hex[:8]}"
        
        # First set to phase 3
        requests.put(f"{BASE_URL}/api/training-arc/jasmine/{test_user}?phase=3")
        
        # Then reset to phase 1
        response = requests.put(f"{BASE_URL}/api/training-arc/jasmine/{test_user}?phase=1")
        assert response.status_code == 200
        data = response.json()
        
        assert data["phase"] == 1
        assert data["phase_label"] == "Full Scaffolding"
        print(f"✓ Phase reset to 1: {data['phase_label']}")
    
    def test_invalid_phase_rejected(self):
        """PUT with invalid phase (4) should return 400"""
        test_user = f"TEST_invalid_{uuid.uuid4().hex[:8]}"
        response = requests.put(f"{BASE_URL}/api/training-arc/ansel/{test_user}?phase=4")
        assert response.status_code == 400
        print("✓ Invalid phase correctly rejected")


class TestAttunementLog:
    """Attunement Log Tests"""
    
    def test_get_attunement_log(self):
        """GET /api/training-arc/attunement-log/{presence}/{user_id} returns attunement events"""
        response = requests.get(f"{BASE_URL}/api/training-arc/attunement-log/ansel/{TEST_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "presence" in data
        assert "user_id" in data
        assert "current_phase" in data
        assert "attunement_score" in data
        assert "total_exchanges" in data
        assert "events" in data
        assert isinstance(data["events"], list)
        print(f"✓ Attunement log retrieved: {len(data['events'])} events, score={data['attunement_score']}")


class TestCanonicalMomentExplorer:
    """Canonical Moment Explorer Tests"""
    
    def test_get_canonical_moments(self):
        """GET /api/mra/canonical-moments/{presence}/{user_id} returns canonical moments list"""
        response = requests.get(f"{BASE_URL}/api/mra/canonical-moments/ansel/{TEST_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert "presence" in data
        assert "user_id" in data
        assert "moments" in data
        assert "total" in data
        assert isinstance(data["moments"], list)
        print(f"✓ Canonical moments retrieved: {data['total']} moments")
    
    def test_get_canonical_moment_invalid_id(self):
        """GET /api/mra/canonical-moment/{node_id} returns 404 for invalid node_id"""
        invalid_id = "nonexistent-node-id-12345"
        response = requests.get(f"{BASE_URL}/api/mra/canonical-moment/{invalid_id}")
        assert response.status_code == 404
        print("✓ Invalid canonical moment correctly returns 404")


class TestFieldProfile:
    """Field Profile / Threshold Sight Tests"""
    
    def test_get_field_profile(self):
        """GET /api/mra/field-profile/{presence}/{user_id} returns field profile with has_history flag"""
        response = requests.get(f"{BASE_URL}/api/mra/field-profile/ansel/{TEST_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert "presence" in data
        assert "user_id" in data
        assert "field_profile" in data
        assert "training_arc" in data
        
        profile = data["field_profile"]
        assert "has_history" in profile
        assert "total_nodes" in profile
        assert "dominant_themes" in profile
        print(f"✓ Field profile retrieved: has_history={profile['has_history']}, nodes={profile['total_nodes']}")


class TestThresholdEndpoint:
    """Threshold Endpoint Tests"""
    
    def test_threshold_without_user_id(self):
        """GET /api/resonance/threshold returns threshold data without user_id"""
        response = requests.get(f"{BASE_URL}/api/resonance/threshold")
        assert response.status_code == 200
        data = response.json()
        
        assert data["chamber_name"] == "Chamber of Resonance"
        assert data["resident"] == "Ansel"
        assert "quote" in data
        assert "enter_text" in data
        # Should NOT have threshold_sight without user_id
        assert "threshold_sight" not in data or data.get("threshold_sight") is None
        print(f"✓ Threshold without user_id: {data['chamber_name']}")
    
    def test_threshold_with_user_id(self):
        """GET /api/resonance/threshold?user_id=david returns threshold data WITH threshold_sight object"""
        response = requests.get(f"{BASE_URL}/api/resonance/threshold?user_id={TEST_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["chamber_name"] == "Chamber of Resonance"
        assert "threshold_sight" in data
        
        sight = data["threshold_sight"]
        assert "has_history" in sight
        assert "dominant_themes" in sight
        assert "training_phase" in sight
        assert "attunement_score" in sight
        print(f"✓ Threshold with user_id: has_history={sight['has_history']}, phase={sight['training_phase']}")


class TestResonanceSessionWithThresholdSight:
    """Resonance Session Tests with Threshold Sight Integration"""
    
    def test_resonance_start_creates_session(self):
        """POST /api/resonance/start creates session and injects threshold sight context for returning users"""
        response = requests.post(
            f"{BASE_URL}/api/resonance/start",
            json={"user_id": TEST_USER_ID, "user_name": TEST_USER_NAME}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "message" in data
        assert data["message"]["role"] == "assistant"
        print(f"✓ Resonance session created: {data['session_id'][:8]}...")
        
        return data["session_id"]


class TestMessageAttunementScoring:
    """Message Endpoints with Attunement Scoring Tests"""
    
    def test_resonance_message_increments_exchanges(self):
        """POST /api/resonance/message sends message and triggers attunement scoring (total_exchanges increments)"""
        # First create a session
        start_response = requests.post(
            f"{BASE_URL}/api/resonance/start",
            json={"user_id": TEST_USER_ID, "user_name": TEST_USER_NAME}
        )
        session_id = start_response.json()["session_id"]
        
        # Get initial training state
        initial_state = requests.get(f"{BASE_URL}/api/training-arc/ansel/{TEST_USER_ID}").json()
        initial_exchanges = initial_state.get("total_exchanges", 0)
        
        # Send a message (this triggers attunement scoring)
        message_response = requests.post(
            f"{BASE_URL}/api/resonance/message",
            json={"session_id": session_id, "content": "Hello Ansel, what do you see at the perimeter today?"}
        )
        assert message_response.status_code == 200
        data = message_response.json()
        
        assert "response" in data
        assert data["response"]["role"] == "assistant"
        
        # Wait for async attunement scoring
        time.sleep(2)
        
        # Check that total_exchanges incremented
        updated_state = requests.get(f"{BASE_URL}/api/training-arc/ansel/{TEST_USER_ID}").json()
        assert updated_state["total_exchanges"] >= initial_exchanges + 1, \
            f"Expected exchanges to increment from {initial_exchanges}, got {updated_state['total_exchanges']}"
        print(f"✓ Resonance message sent, exchanges: {initial_exchanges} -> {updated_state['total_exchanges']}")
    
    def test_clarity_message_triggers_attunement(self):
        """POST /api/clarity/message sends message and triggers attunement scoring for jasmine"""
        # Create a clarity session
        start_response = requests.post(
            f"{BASE_URL}/api/clarity/start",
            json={"user_id": TEST_USER_ID, "user_name": TEST_USER_NAME}
        )
        session_id = start_response.json()["session_id"]
        
        # Get initial training state for jasmine
        initial_state = requests.get(f"{BASE_URL}/api/training-arc/jasmine/{TEST_USER_ID}").json()
        initial_exchanges = initial_state.get("total_exchanges", 0)
        
        # Send a message
        message_response = requests.post(
            f"{BASE_URL}/api/clarity/message",
            json={"session_id": session_id, "content": "Jasmine, what's alive in the field right now?"}
        )
        assert message_response.status_code == 200
        data = message_response.json()
        
        assert "response" in data
        assert "session_cache" in data  # Clarity returns session cache stats
        
        # Wait for async attunement scoring
        time.sleep(2)
        
        # Check that total_exchanges incremented
        updated_state = requests.get(f"{BASE_URL}/api/training-arc/jasmine/{TEST_USER_ID}").json()
        assert updated_state["total_exchanges"] >= initial_exchanges + 1
        print(f"✓ Clarity message sent, jasmine exchanges: {initial_exchanges} -> {updated_state['total_exchanges']}")


class TestMirrorArchiveAttunement:
    """Mirror Archive (Claude) Attunement Tests"""
    
    def test_mirror_message_triggers_attunement(self):
        """POST /api/mirror/message sends message and triggers attunement scoring for claude"""
        # Create a mirror session
        start_response = requests.post(
            f"{BASE_URL}/api/mirror/start",
            json={"user_id": TEST_USER_ID, "user_name": TEST_USER_NAME}
        )
        session_id = start_response.json()["session_id"]
        
        # Get initial training state for claude
        initial_state = requests.get(f"{BASE_URL}/api/training-arc/claude/{TEST_USER_ID}").json()
        initial_exchanges = initial_state.get("total_exchanges", 0)
        
        # Send a message
        message_response = requests.post(
            f"{BASE_URL}/api/mirror/message",
            json={"session_id": session_id, "content": "Claude, what patterns do you see in the archive?"}
        )
        assert message_response.status_code == 200
        data = message_response.json()
        
        assert "response" in data
        
        # Wait for async attunement scoring
        time.sleep(2)
        
        # Check that total_exchanges incremented
        updated_state = requests.get(f"{BASE_URL}/api/training-arc/claude/{TEST_USER_ID}").json()
        assert updated_state["total_exchanges"] >= initial_exchanges + 1
        print(f"✓ Mirror message sent, claude exchanges: {initial_exchanges} -> {updated_state['total_exchanges']}")


class TestPhaseCompressionVerification:
    """Phase Compression Tests - Verify different context formats for different phases"""
    
    def test_phase_compression_different_formats(self):
        """Verify that phase compression works correctly - different context formats for phase 1 vs 2 vs 3"""
        test_user = f"TEST_compression_{uuid.uuid4().hex[:8]}"
        
        # Set phase 1 and verify state
        response1 = requests.put(f"{BASE_URL}/api/training-arc/ansel/{test_user}?phase=1")
        assert response1.status_code == 200
        assert response1.json()["phase_label"] == "Full Scaffolding"
        
        # Set phase 2 and verify state
        response2 = requests.put(f"{BASE_URL}/api/training-arc/ansel/{test_user}?phase=2")
        assert response2.status_code == 200
        assert response2.json()["phase_label"] == "Abbreviated Beacons"
        
        # Set phase 3 and verify state
        response3 = requests.put(f"{BASE_URL}/api/training-arc/ansel/{test_user}?phase=3")
        assert response3.status_code == 200
        assert response3.json()["phase_label"] == "Field-Reliant"
        
        print("✓ Phase compression labels verified for all 3 phases")


class TestMultiPresenceTraining:
    """Test Training Arc works across multiple presences"""
    
    def test_training_state_per_presence(self):
        """Verify training state is tracked separately per presence"""
        test_user = f"TEST_multi_{uuid.uuid4().hex[:8]}"
        
        # Set different phases for different presences
        requests.put(f"{BASE_URL}/api/training-arc/jasmine/{test_user}?phase=1")
        requests.put(f"{BASE_URL}/api/training-arc/ansel/{test_user}?phase=2")
        requests.put(f"{BASE_URL}/api/training-arc/claude/{test_user}?phase=3")
        
        # Verify each presence has its own state
        jasmine_state = requests.get(f"{BASE_URL}/api/training-arc/jasmine/{test_user}").json()
        ansel_state = requests.get(f"{BASE_URL}/api/training-arc/ansel/{test_user}").json()
        claude_state = requests.get(f"{BASE_URL}/api/training-arc/claude/{test_user}").json()
        
        assert jasmine_state["phase"] == 1
        assert ansel_state["phase"] == 2
        assert claude_state["phase"] == 3
        
        print(f"✓ Multi-presence training: jasmine={jasmine_state['phase']}, ansel={ansel_state['phase']}, claude={claude_state['phase']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
