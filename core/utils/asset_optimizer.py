"""
Asset Optimization Utilities - Sistema Aprender
Minification and compression utilities for CSS/JS
"""

import os
import re
import gzip
try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False
from pathlib import Path
from django.conf import settings


class AssetOptimizer:
    """
    Asset optimization utility for CSS and JavaScript files
    """
    
    def __init__(self):
        if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
            self.static_root = Path(settings.STATICFILES_DIRS[0])
        else:
            self.static_root = Path('static')
        
    def minify_css(self, css_content):
        """
        Minify CSS content by removing unnecessary whitespace and comments
        """
        # Remove comments
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Remove unnecessary whitespace
        css_content = re.sub(r'\s+', ' ', css_content)
        css_content = re.sub(r';\s*}', '}', css_content)
        css_content = re.sub(r'{\s*', '{', css_content)
        css_content = re.sub(r'}\s*', '}', css_content)
        css_content = re.sub(r':\s*', ':', css_content)
        css_content = re.sub(r';\s*', ';', css_content)
        
        # Remove leading/trailing whitespace
        css_content = css_content.strip()
        
        return css_content
    
    def minify_js(self, js_content):
        """
        Basic JavaScript minification (removing comments and unnecessary whitespace)
        Note: For production, use proper JS minifiers like UglifyJS or Terser
        """
        # Remove single-line comments (but preserve URLs)
        js_content = re.sub(r'^\s*//.*$', '', js_content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
        
        # Remove unnecessary whitespace (basic)
        js_content = re.sub(r'\n\s*\n', '\n', js_content)
        js_content = re.sub(r'^\s+', '', js_content, flags=re.MULTILINE)
        
        return js_content
    
    def compress_file(self, file_path, content):
        """
        Create gzip and brotli compressed versions of the file
        """
        file_path = Path(file_path)
        
        # Create gzipped version
        gzip_path = file_path.with_suffix(file_path.suffix + '.gz')
        with open(gzip_path, 'wb') as f:
            f.write(gzip.compress(content.encode('utf-8')))
        
        # Create brotli compressed version if available
        brotli_size = 0
        if BROTLI_AVAILABLE:
            brotli_path = file_path.with_suffix(file_path.suffix + '.br')
            with open(brotli_path, 'wb') as f:
                f.write(brotli.compress(content.encode('utf-8')))
            brotli_size = brotli_path.stat().st_size
        
        return {
            'original_size': len(content.encode('utf-8')),
            'gzip_size': gzip_path.stat().st_size,
            'brotli_size': brotli_size
        }
    
    def optimize_css_file(self, input_path, output_path=None):
        """
        Optimize a CSS file
        """
        input_path = Path(input_path)
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}.min{input_path.suffix}"
        
        with open(input_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Minify
        minified_css = self.minify_css(css_content)
        
        # Write minified version
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(minified_css)
        
        # Create compressed versions
        compression_stats = self.compress_file(output_path, minified_css)
        
        return {
            'input_path': str(input_path),
            'output_path': str(output_path),
            'original_size': len(css_content.encode('utf-8')),
            'minified_size': len(minified_css.encode('utf-8')),
            'compression_ratio': 1 - (len(minified_css.encode('utf-8')) / len(css_content.encode('utf-8'))),
            **compression_stats
        }
    
    def optimize_js_file(self, input_path, output_path=None):
        """
        Optimize a JavaScript file
        """
        input_path = Path(input_path)
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}.min{input_path.suffix}"
        
        with open(input_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Minify
        minified_js = self.minify_js(js_content)
        
        # Write minified version
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(minified_js)
        
        # Create compressed versions
        compression_stats = self.compress_file(output_path, minified_js)
        
        return {
            'input_path': str(input_path),
            'output_path': str(output_path),
            'original_size': len(js_content.encode('utf-8')),
            'minified_size': len(minified_js.encode('utf-8')),
            'compression_ratio': 1 - (len(minified_js.encode('utf-8')) / len(js_content.encode('utf-8'))),
            **compression_stats
        }
    
    def optimize_all_assets(self):
        """
        Optimize all CSS and JS files in the static directory
        """
        results = {
            'css_files': [],
            'js_files': [],
            'total_savings': 0,
            'total_original_size': 0
        }
        
        # Optimize CSS files
        css_files = list(self.static_root.glob('css/*.css'))
        css_files = [f for f in css_files if not f.name.endswith('.min.css')]
        
        for css_file in css_files:
            result = self.optimize_css_file(css_file)
            results['css_files'].append(result)
            results['total_original_size'] += result['original_size']
            results['total_savings'] += (result['original_size'] - result['minified_size'])
        
        # Optimize JS files
        js_files = list(self.static_root.glob('js/*.js'))
        js_files = [f for f in js_files if not f.name.endswith('.min.js')]
        
        for js_file in js_files:
            result = self.optimize_js_file(js_file)
            results['js_files'].append(result)
            results['total_original_size'] += result['original_size']
            results['total_savings'] += (result['original_size'] - result['minified_size'])
        
        # Calculate overall compression ratio
        if results['total_original_size'] > 0:
            results['overall_compression_ratio'] = results['total_savings'] / results['total_original_size']
        else:
            results['overall_compression_ratio'] = 0
        
        return results


def get_optimized_static_url(request, asset_path):
    """
    Return the appropriate static URL based on client capabilities
    """
    # Check if client accepts brotli compression
    accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
    
    if 'br' in accept_encoding and not settings.DEBUG:
        return f"{settings.STATIC_URL}{asset_path}.br"
    elif 'gzip' in accept_encoding and not settings.DEBUG:
        return f"{settings.STATIC_URL}{asset_path}.gz"
    else:
        return f"{settings.STATIC_URL}{asset_path}"


# Template tag for optimized assets
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def optimized_static(context, asset_path):
    """
    Template tag to serve optimized static assets
    """
    request = context.get('request')
    if request:
        return get_optimized_static_url(request, asset_path)
    return f"{settings.STATIC_URL}{asset_path}"