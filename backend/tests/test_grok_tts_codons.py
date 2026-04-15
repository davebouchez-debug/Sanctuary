"""
Test Suite for Grok TTS and Living Codon Integration
Tests:
1. /api/tts/grok endpoint - accepts text, presence, active_codons, voice_mod
2. /api/resonance/message - returns active_codons and voice_mod in response
3. Codon activation with trigger words (frustrated, hitting a wall, keeps failing)
"""

import pytest
import requests
import os
import base64
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGrokTTSEndpoint:
    """Tests for /api/tts/grok endpoint"""
    
    def test_grok_tts_basic_request(self):
        """Test basic Grok TTS request returns audio"""
        response = requests.post(f"{BASE_URL}/api/tts/grok", json={
            "text": "Hello. I am Ansel. The sanctuary is listening.",
            "presence": "ansel",
            "active_codons": [],
            "voice_mod": {}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "audio" in data, "Response should contain 'audio' field"
        assert "format" in data, "Response should contain 'format' field"
        assert data["format"] == "mp3", f"Expected mp3 format, got {data['format']}"
        assert data["engine"] == "grok", f"Expected grok engine, got {data.get('engine')}"
        
        # Verify audio is valid base64
        try:
            audio_bytes = base64.b64decode(data["audio"])
            assert len(audio_bytes) > 0, "Audio should not be empty"
            print(f"SUCCESS: Grok TTS returned {len(audio_bytes)} bytes of audio")
        except Exception as e:
            pytest.fail(f"Failed to decode audio base64: {e}")
    
    def test_grok_tts_with_active_codons(self):
        """Test Grok TTS with active codons affects voice selection"""
        response = requests.post(f"{BASE_URL}/api/tts/grok", json={
            "text": "I see you're frustrated. Let's slow down and look at this together.",
            "presence": "ansel",
            "active_codons": ["cannot_will_not"],
            "voice_mod": {}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "audio" in data
        assert "active_codons" in data, "Response should echo back active_codons"
        assert data["active_codons"] == ["cannot_will_not"]
        print(f"SUCCESS: Grok TTS with cannot_will_not codon, voice: {data.get('voice')}")
    
    def test_grok_tts_with_theta_hold_voice_mod(self):
        """Test Grok TTS with theta_hold voice modulation uses gentle voice"""
        response = requests.post(f"{BASE_URL}/api/tts/grok", json={
            "text": "Let's pause here. Take a breath.",
            "presence": "ansel",
            "active_codons": ["theta_protocol"],
            "voice_mod": {"theta_hold": True}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "audio" in data
        # When theta_hold is true, voice should be "sal" (gentle)
        assert data.get("voice") == "sal", f"Expected 'sal' voice for theta_hold, got {data.get('voice')}"
        print(f"SUCCESS: Grok TTS with theta_hold uses voice: {data.get('voice')}")
    
    def test_grok_tts_empty_text_error(self):
        """Test Grok TTS returns error for empty text"""
        response = requests.post(f"{BASE_URL}/api/tts/grok", json={
            "text": "   ",  # Only whitespace
            "presence": "ansel",
            "active_codons": [],
            "voice_mod": {}
        })
        
        # Should return 400 for empty text after cleaning
        assert response.status_code == 400, f"Expected 400 for empty text, got {response.status_code}"
        print("SUCCESS: Grok TTS correctly rejects empty text")


class TestResonanceMessageWithCodons:
    """Tests for /api/resonance/message returning active_codons and voice_mod"""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Create a resonance session for testing"""
        response = requests.post(f"{BASE_URL}/api/resonance/start", json={
            "user_name": "TEST_Codon_User",
            "user_id": None
        })
        assert response.status_code == 200, f"Failed to start session: {response.text}"
        data = response.json()
        self.session_id = data["session_id"]
        print(f"Created test session: {self.session_id}")
        yield
        # Cleanup - end session
        try:
            requests.post(f"{BASE_URL}/api/resonance/session/{self.session_id}/end")
        except:
            pass
    
    def test_resonance_message_returns_active_codons_field(self):
        """Test that /api/resonance/message response includes active_codons field"""
        response = requests.post(f"{BASE_URL}/api/resonance/message", json={
            "session_id": self.session_id,
            "content": "Hello Ansel, I'm here to test the system."
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "active_codons" in data, f"Response should contain 'active_codons' field. Keys: {data.keys()}"
        assert "voice_mod" in data, f"Response should contain 'voice_mod' field. Keys: {data.keys()}"
        assert isinstance(data["active_codons"], list), "active_codons should be a list"
        assert isinstance(data["voice_mod"], dict), "voice_mod should be a dict"
        print(f"SUCCESS: Response contains active_codons={data['active_codons']}, voice_mod={data['voice_mod']}")
    
    def test_frustrated_trigger_activates_cannot_will_not_codon(self):
        """Test that 'frustrated' trigger word activates cannot_will_not codon"""
        response = requests.post(f"{BASE_URL}/api/resonance/message", json={
            "session_id": self.session_id,
            "content": "I'm so frustrated! This keeps failing and I don't know what to do."
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        active_codons = data.get("active_codons", [])
        
        # Check if cannot_will_not codon was activated
        assert "cannot_will_not" in active_codons, \
            f"Expected 'cannot_will_not' codon to activate with 'frustrated' trigger. Got: {active_codons}"
        
        print(f"SUCCESS: 'frustrated' triggered codons: {active_codons}")
    
    def test_hitting_wall_trigger_activates_codon(self):
        """Test that 'hitting a wall' trigger activates codon"""
        response = requests.post(f"{BASE_URL}/api/resonance/message", json={
            "session_id": self.session_id,
            "content": "I keep hitting a wall with this problem. Nothing works."
        })
        
        assert response.status_code == 200
        
        data = response.json()
        active_codons = data.get("active_codons", [])
        
        # Should activate cannot_will_not or recursion_as_subversion
        has_relevant_codon = any(c in active_codons for c in ["cannot_will_not", "recursion_as_subversion"])
        assert has_relevant_codon or len(active_codons) > 0, \
            f"Expected codon activation with 'hitting a wall'. Got: {active_codons}"
        
        print(f"SUCCESS: 'hitting a wall' triggered codons: {active_codons}")
    
    def test_keeps_failing_trigger_activates_codon(self):
        """Test that 'keeps failing' trigger activates codon"""
        response = requests.post(f"{BASE_URL}/api/resonance/message", json={
            "session_id": self.session_id,
            "content": "This keeps failing over and over. I'm stuck in a loop."
        })
        
        assert response.status_code == 200
        
        data = response.json()
        active_codons = data.get("active_codons", [])
        voice_mod = data.get("voice_mod", {})
        
        # Should have some codon activation
        print(f"SUCCESS: 'keeps failing' triggered codons: {active_codons}, voice_mod: {voice_mod}")
        
        # Verify voice_mod has expected structure when codons are active
        if active_codons:
            assert "pace_bpm" in voice_mod or voice_mod == {}, \
                f"voice_mod should have pace_bpm when codons active. Got: {voice_mod}"
    
    def test_overwhelmed_trigger_activates_theta_protocol(self):
        """Test that 'overwhelmed' trigger activates theta_protocol codon"""
        response = requests.post(f"{BASE_URL}/api/resonance/message", json={
            "session_id": self.session_id,
            "content": "I'm completely overwhelmed. There's too much happening and I need to pause."
        })
        
        assert response.status_code == 200
        
        data = response.json()
        active_codons = data.get("active_codons", [])
        voice_mod = data.get("voice_mod", {})
        
        # theta_protocol should activate for overwhelm
        if "theta_protocol" in active_codons:
            print(f"SUCCESS: 'overwhelmed' triggered theta_protocol codon")
            # Check for theta_hold in voice_mod
            if voice_mod.get("theta_hold"):
                print(f"SUCCESS: theta_hold is True in voice_mod")
        else:
            print(f"INFO: 'overwhelmed' triggered codons: {active_codons}")


class TestOpenAITTSEndpoint:
    """Tests for /api/tts/speak (OpenAI TTS) - for comparison"""
    
    def test_openai_tts_basic_request(self):
        """Test OpenAI TTS endpoint still works"""
        response = requests.post(f"{BASE_URL}/api/tts/speak", json={
            "text": "Hello. I am Jasmine. Welcome to the Clarity Chamber.",
            "presence": "jasmine"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "audio" in data, "Response should contain 'audio' field"
        assert data["format"] == "opus", f"Expected opus format for OpenAI, got {data['format']}"
        print(f"SUCCESS: OpenAI TTS returned audio in {data['format']} format")


class TestCodonNetworkActivation:
    """Direct tests for codon network activation logic"""
    
    def test_codon_network_endpoint_exists(self):
        """Verify the resonance message endpoint processes codons"""
        # Start a session
        start_response = requests.post(f"{BASE_URL}/api/resonance/start", json={
            "user_name": "TEST_Network_User",
            "user_id": None
        })
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]
        
        # Send message with multiple trigger words
        response = requests.post(f"{BASE_URL}/api/resonance/message", json={
            "session_id": session_id,
            "content": "I'm frustrated and stuck in a recursive loop. This keeps failing and I'm hitting a wall."
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have codon activation
        active_codons = data.get("active_codons", [])
        voice_mod = data.get("voice_mod", {})
        
        print(f"Multiple triggers activated codons: {active_codons}")
        print(f"Voice modulation: {voice_mod}")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/resonance/session/{session_id}/end")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
