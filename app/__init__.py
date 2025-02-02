from flask import Flask
import markdown

def create_app(config=None):
    app = Flask(__name__)
    
    # Add markdown filter to Jinja
    @app.template_filter('markdown')
    def markdown_filter(text):
        return markdown.markdown(text) if text else ""
    
    // ... rest of create_app code ... 