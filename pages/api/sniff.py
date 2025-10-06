import json
import requests
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import urljoin, urlparse
try:
    from bs4 import BeautifulSoup
except ImportError:
    # Fallback if BeautifulSoup is not available
    BeautifulSoup = None

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
            
            if not data or 'url' not in data:
                self.wfile.write(json.dumps({"error": "Missing URL in request"}).encode())
                return
            
            url = data['url']
            
            # Use the simplified sniffer
            result = self.sniff_url_simple(url)
            self.wfile.write(json.dumps(result).encode())
            
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

    def sniff_url_simple(self, url):
        """
        Simplified website component sniffer using requests and basic HTML parsing
        """
        try:
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Fetch the webpage
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            if BeautifulSoup:
                # Parse HTML with BeautifulSoup if available
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract CSS from style tags and linked stylesheets
                css_content = ""
                
                # Get inline styles
                for style_tag in soup.find_all('style'):
                    if style_tag.string:
                        css_content += style_tag.string + "\n"
                
                # Try to fetch external stylesheets (limited for security)
                for link in soup.find_all('link', rel='stylesheet'):
                    href = link.get('href')
                    if href:
                        try:
                            css_url = urljoin(url, href)
                            css_response = requests.get(css_url, headers=headers, timeout=5)
                            if css_response.status_code == 200:
                                css_content += css_response.text + "\n"
                        except:
                            continue  # Skip if can't fetch CSS
                
                # Find interesting components
                results = {}
                
                # Look for common component patterns
                components_to_find = [
                    ('header', ['header', 'nav', '.navbar', '.header']),
                    ('hero-section', ['.hero', '.banner', '.jumbotron']),
                    ('card', ['.card', '.product', '.item']),
                    ('button', ['button', '.btn', '.button']),
                    ('form', ['form', '.form', '.contact-form']),
                    ('footer', ['footer', '.footer'])
                ]
                
                for component_name, selectors in components_to_find:
                    for selector in selectors:
                        elements = soup.select(selector)
                        if elements:
                            # Take the first matching element
                            element = elements[0]
                            
                            # Extract HTML
                            element_html = str(element)
                            
                            # Extract relevant CSS (simplified)
                            element_css = self.extract_relevant_css(css_content, element, soup)
                            
                            # Clean up the HTML and CSS
                            element_html = self.clean_html(element_html)
                            element_css = self.clean_css(element_css)
                            
                            if element_html and len(element_html) > 50:  # Only include substantial components
                                results[component_name] = {
                                    "html": element_html,
                                    "css": element_css,
                                    "description": f"Extracted {component_name} component from {urlparse(url).netloc}"
                                }
                                break  # Found one, move to next component type
                
                return results if results else {"message": "No components found on this page"}
            else:
                # Fallback without BeautifulSoup - basic regex parsing
                return {"message": "Basic HTML parsing not available - BeautifulSoup required for full functionality"}
                
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")
        except Exception as e:
            raise Exception(f"Error analyzing website: {str(e)}")

    def extract_relevant_css(self, css_content, element, soup):
        """Extract CSS rules that might apply to the element"""
        if not css_content:
            return ""
        
        # Get element classes and ID
        classes = element.get('class', [])
        element_id = element.get('id', '')
        tag_name = element.name
        
        relevant_css = []
        
        # Simple CSS extraction - look for rules that match our element
        css_rules = re.findall(r'([^{}]+)\s*\{([^{}]*)\}', css_content)
        
        for selector, rules in css_rules:
            selector = selector.strip()
            
            # Check if selector might apply to our element
            if (tag_name in selector or 
                any(f'.{cls}' in selector for cls in classes) or
                (element_id and f'#{element_id}' in selector) or
                any(parent.name in selector for parent in element.parents if parent.name)):
                
                relevant_css.append(f"{selector} {{\n{rules.strip()}\n}}")
        
        return "\n\n".join(relevant_css[:10])  # Limit to first 10 rules

    def clean_html(self, html):
        """Clean up HTML for better presentation"""
        # Remove script tags and their content
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # Clean up whitespace
        html = re.sub(r'\s+', ' ', html)
        html = html.strip()
        
        return html

    def clean_css(self, css):
        """Clean up CSS for better presentation"""
        if not css:
            return ""
        
        # Remove comments
        css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
        
        # Clean up whitespace
        css = re.sub(r'\s+', ' ', css)
        css = css.strip()
        
        return css

