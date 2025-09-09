"""
Django Management Command - Optimize Static Assets
==================================================

Command to minify and compress CSS/JS files for better performance.

Usage:
    python manage.py optimize_assets
    python manage.py optimize_assets --verbose
    python manage.py optimize_assets --force

Author: Claude Code - Sistema Aprender
Date: Janeiro 2025
"""

from django.core.management.base import BaseCommand
from core.utils.asset_optimizer import AssetOptimizer


class Command(BaseCommand):
    help = "Optimize static assets (CSS/JS) for better performance"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reoptimization of already optimized files'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed optimization results'
        )

    def handle(self, *args, **options):
        self.stdout.write("Optimizing Static Assets...")
        self.stdout.write("=" * 60)
        
        optimizer = AssetOptimizer()
        
        try:
            results = optimizer.optimize_all_assets()
            
            # Display results
            self.stdout.write(f"[OK] CSS Files Optimized: {len(results['css_files'])}")
            self.stdout.write(f"[OK] JS Files Optimized: {len(results['js_files'])}")
            
            if options['verbose']:
                self.stdout.write("\nDetailed Results:")
                
                # CSS files
                if results['css_files']:
                    self.stdout.write("\nCSS Files:")
                    for css_result in results['css_files']:
                        original_kb = css_result['original_size'] / 1024
                        minified_kb = css_result['minified_size'] / 1024
                        savings_percent = css_result['compression_ratio'] * 100
                        
                        self.stdout.write(
                            f"  {css_result['input_path']}: "
                            f"{original_kb:.1f}KB -> {minified_kb:.1f}KB "
                            f"({savings_percent:.1f}% smaller)"
                        )
                
                # JS files  
                if results['js_files']:
                    self.stdout.write("\nJS Files:")
                    for js_result in results['js_files']:
                        original_kb = js_result['original_size'] / 1024
                        minified_kb = js_result['minified_size'] / 1024
                        savings_percent = js_result['compression_ratio'] * 100
                        
                        self.stdout.write(
                            f"  {js_result['input_path']}: "
                            f"{original_kb:.1f}KB -> {minified_kb:.1f}KB "
                            f"({savings_percent:.1f}% smaller)"
                        )
            
            # Overall statistics
            total_original_kb = results['total_original_size'] / 1024
            total_savings_kb = results['total_savings'] / 1024
            overall_percent = results['overall_compression_ratio'] * 100
            
            self.stdout.write(f"\nOverall Statistics:")
            self.stdout.write(f"  Total Original Size: {total_original_kb:.1f}KB")
            self.stdout.write(f"  Total Savings: {total_savings_kb:.1f}KB")
            self.stdout.write(f"  Overall Compression: {overall_percent:.1f}%")
            
            self.stdout.write("[OK] Asset optimization completed successfully!")
            
            # Additional compression info
            if results['css_files'] or results['js_files']:
                self.stdout.write("\nCompression formats created:")
                self.stdout.write("  .gz (gzip) - Widely supported")
                self.stdout.write("  .br (brotli) - Better compression, modern browsers")
                self.stdout.write("\nUse optimized_static template tag to serve compressed assets.")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Asset optimization failed: {e}")
            raise