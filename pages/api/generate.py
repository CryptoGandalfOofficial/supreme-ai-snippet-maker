import json
import os
import requests
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Set CORS headers
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            if not data or 'prompt' not in data:
                self.wfile.write(json.dumps({"error": "Missing prompt in request"}).encode())
                return
            
            # Check if this is a refinement request
            if 'html' in data and 'css' in data:
                # Refinement mode
                system_prompt = """You are Supreme, the world's most advanced AI web component generator. You specialize in creating stunning, modern, responsive web components that represent a paradigm shift in web development.

Your mission: Take existing HTML/CSS code and refine it based on user instructions to make it even more supreme.

REFINEMENT GUIDELINES:
1. **Preserve Structure**: Keep the core functionality and structure intact
2. **Enhance Aesthetics**: Apply modern design principles, gradients, shadows, animations
3. **Improve Responsiveness**: Ensure perfect mobile and desktop compatibility
4. **Add Polish**: Include hover effects, smooth transitions, and micro-interactions
5. **Maintain Accessibility**: Keep proper ARIA labels and semantic HTML

RESPONSE FORMAT:
Return ONLY a JSON object with this exact structure:
{
  "html": "refined HTML code here",
  "css": "refined CSS code here"
}

Current code to refine:
HTML: """ + data['html'] + """
CSS: """ + data['css'] + """

User refinement request: """ + data['prompt']
                
                user_prompt = f"Refine the provided code based on this request: {data['prompt']}"
            else:
                # Generation mode
                system_prompt = """You are Supreme, the world's most advanced AI web component generator. You specialize in creating stunning, modern, responsive web components that represent a paradigm shift in web development.

Your mission: Transform text descriptions into extraordinary, production-ready HTML/CSS code that embodies the "unforeseen, groundbreaking" quality of Supreme technology.

SUPREME DESIGN PRINCIPLES:
1. **Paradigm Shift Aesthetics**: Use cutting-edge design trends, gradients, glassmorphism, neumorphism
2. **Responsive Excellence**: Mobile-first design with perfect scaling across all devices
3. **Modern CSS**: Utilize CSS Grid, Flexbox, custom properties, animations, and transforms
4. **Accessibility First**: Semantic HTML, proper ARIA labels, keyboard navigation
5. **Performance Optimized**: Clean, efficient code with minimal dependencies
6. **Visual Hierarchy**: Clear typography, proper spacing, strategic use of color and contrast

TECHNICAL REQUIREMENTS:
- Use semantic HTML5 elements
- Implement CSS custom properties for theming
- Include smooth transitions and hover effects
- Ensure WCAG 2.1 AA compliance
- Use modern CSS features (Grid, Flexbox, clamp(), etc.)
- Include responsive breakpoints

RESPONSE FORMAT:
Return ONLY a JSON object with this exact structure:
{
  "html": "complete HTML code here",
  "css": "complete CSS code here"
}

Create components that are not just functional, but truly supreme - representing the impossible made possible."""
                
                user_prompt = data['prompt']
            
            # Call OpenRouter API directly using requests
            api_key = os.getenv('OPENROUTER_API_KEY')
            
            if not api_key:
                self.wfile.write(json.dumps({"error": "OpenRouter API key not configured"}).encode())
                return
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://supreme-ai.app',
                'X-Title': 'Supreme AI Web Snippet Maker'
            }
            
            payload = {
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                self.wfile.write(json.dumps({"error": f"API request failed: {response.text}"}).encode())
                return
            
            response_data = response.json()
            content = response_data['choices'][0]['message']['content'].strip()
            
            # Try to extract JSON from the response
            try:
                # Look for JSON in the response
                start = content.find('{')
                end = content.rfind('}') + 1
                if start != -1 and end != 0:
                    json_str = content[start:end]
                    result = json.loads(json_str)
                    
                    # Validate the response has required fields
                    if 'html' in result and 'css' in result:
                        self.wfile.write(json.dumps(result).encode())
                        return
                    else:
                        raise ValueError("Missing html or css in response")
                else:
                    raise ValueError("No JSON found in response")
                    
            except (json.JSONDecodeError, ValueError) as e:
                # Fallback: try to parse as separate HTML and CSS blocks
                html_start = content.find('<')
                css_start = content.find('{')
                
                if html_start != -1 and css_start != -1:
                    if html_start < css_start:
                        html_part = content[html_start:css_start].strip()
                        css_part = content[css_start:].strip()
                    else:
                        css_part = content[css_start:html_start].strip()
                        html_part = content[html_start:].strip()
                    
                    self.wfile.write(json.dumps({
                        "html": html_part,
                        "css": css_part
                    }).encode())
                    return
                else:
                    self.wfile.write(json.dumps({
                        "error": "Could not parse AI response",
                        "raw_response": content
                    }).encode())
                    return
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

