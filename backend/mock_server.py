import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class MockAIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/pipeline/rank':
            # Parse multipart form data just to consume it
            content_type = self.headers.get('Content-Type')
            if 'multipart/form-data' in content_type:
                pass
            
            # Create mock response exactly matching the real Python backend schema
            mock_response = [
                {
                    "rank": 1,
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "role": "Senior Engineer",
                    "percentile": 99.5,
                    "pr_score": 95.0,
                    "github_score": 98.0,
                    "dsa_score": 92.0,
                    "verdict": "HIRE",
                    "summary": "Excellent fit based on AI analysis. Strong GitHub track record.",
                    "online_links": "github.com/janedoe, linkedin.com/in/janedoe",
                    "skills": [
                        {"name": "React", "claimed": 5, "verified": 5},
                        {"name": "Python", "claimed": 4, "verified": 4}
                    ],
                    "skill_scores": [
                        {"name": "React", "claimed": 5, "verified": 5},
                        {"name": "Python", "claimed": 4, "verified": 4}
                    ],
                    "github_evidence": {
                        "verified": True,
                        "repo_count": 42,
                        "languages": [{"name": "TypeScript", "percentage": 80}],
                        "architecture_score": 90,
                        "ai_usage_level": "High",
                        "last_active": "2026-08-01T00:00:00Z"
                    },
                    "leetcode_stats": {
                        "verified": True,
                        "rating": 1800,
                        "problems_solved": 350,
                        "consistency": 85,
                        "easy": 100,
                        "medium": 200,
                        "hard": 50
                    },
                    "timeline": [
                        {
                            "type": "experience",
                            "title": "Senior Dev",
                            "organization": "Tech Corp",
                            "period": "2020-2026",
                            "description": "Led frontend architecture."
                        }
                    ],
                    "risk_flags": []
                }
            ]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(mock_response).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), MockAIHandler)
    print("Mock AI Server running on port 8000...")
    server.serve_forever()
