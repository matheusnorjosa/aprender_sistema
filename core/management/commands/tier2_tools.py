"""
Django Management Command - TIER 2 Tools
=========================================

Command to test and manage TIER 2 advanced tools:
- Analytics Dashboard with Plotly
- Advanced Security & Cryptography
- TheAlgorithms implementations

Usage:
    python manage.py tier2_tools --test-analytics
    python manage.py tier2_tools --test-security
    python manage.py tier2_tools --generate-dashboard
    python manage.py tier2_tools --test-crypto --password "test123"

Author: Claude Code
Date: Janeiro 2025
"""

import json
import base64
from django.core.management.base import BaseCommand, CommandError
from core.services.analytics_dashboard import (
    educational_analytics,
    get_dashboard_data,
    get_formador_chart,
    get_municipal_chart
)
from core.services.advanced_security import (
    security_utils,
    password_analyzer,
    encrypt_data,
    decrypt_data,
    generate_api_key,
    analyze_password_strength
)


class Command(BaseCommand):
    help = "Test and manage TIER 2 advanced tools"

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-analytics',
            action='store_true',
            help='Test analytics dashboard functionality'
        )
        
        parser.add_argument(
            '--test-security',
            action='store_true',
            help='Test advanced security features'
        )
        
        parser.add_argument(
            '--test-crypto',
            action='store_true',
            help='Test cryptographic functions'
        )
        
        parser.add_argument(
            '--password',
            type=str,
            help='Password to analyze or encrypt with'
        )
        
        parser.add_argument(
            '--generate-dashboard',
            action='store_true',
            help='Generate comprehensive analytics dashboard'
        )
        
        parser.add_argument(
            '--test-ciphers',
            action='store_true',
            help='Test classical cipher algorithms'
        )
        
        parser.add_argument(
            '--encrypt-text',
            type=str,
            help='Text to encrypt using modern cryptography'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all TIER 2 tests'
        )

    def handle(self, *args, **options):
        self.stdout.write("Testing TIER 2 Advanced Tools...")
        
        if options['all']:
            self.test_analytics()
            self.test_security()
            self.test_crypto()
            self.test_ciphers()
        elif options['test_analytics']:
            self.test_analytics()
        elif options['test_security']:
            self.test_security()
        elif options['test_crypto']:
            self.test_crypto(options.get('password'))
        elif options['test_ciphers']:
            self.test_ciphers()
        elif options['generate_dashboard']:
            self.generate_dashboard()
        elif options['encrypt_text']:
            self.test_encryption(options['encrypt_text'])
        else:
            raise CommandError("Please specify a test to run. Use --help for options.")
    
    def test_analytics(self):
        """Test analytics dashboard functionality"""
        self.stdout.write("=" * 60)
        self.stdout.write("TESTING ANALYTICS DASHBOARD")
        self.stdout.write("=" * 60)
        
        try:
            # Test basic analytics service
            if not educational_analytics.enabled:
                self.stdout.write("[WARNING] Plotly not available - analytics limited")
                return
            
            # Get formador performance data
            self.stdout.write("Testing formador performance data...")
            perf_data = educational_analytics.get_formador_performance_data(30)
            
            if 'error' not in perf_data:
                self.stdout.write(f"[OK] Found data for period: {perf_data['period']}")
                self.stdout.write(f"     Formadores in data: {len(perf_data.get('formadores', []))}")
            else:
                self.stdout.write(f"[ERROR] {perf_data['error']}")
            
            # Test municipal distribution
            self.stdout.write("\nTesting municipal distribution...")
            municipal_data = educational_analytics.get_municipal_distribution_data()
            
            if 'error' not in municipal_data:
                self.stdout.write(f"[OK] Found {len(municipal_data.get('municipios', []))} municipalities")
            else:
                self.stdout.write(f"[ERROR] {municipal_data['error']}")
            
            # Test comprehensive dashboard
            self.stdout.write("\nTesting comprehensive dashboard generation...")
            dashboard_data = get_dashboard_data()
            
            if 'error' not in dashboard_data:
                self.stdout.write("[OK] Dashboard data generated successfully")
                self.stdout.write(f"     Statistics: {len(dashboard_data.get('statistics', {}))}")
                self.stdout.write(f"     Charts: {len(dashboard_data.get('charts', {}))}")
                
                # Show some stats
                stats = dashboard_data.get('statistics', {})
                if stats:
                    self.stdout.write("\n     Key Statistics:")
                    for key, value in stats.items():
                        self.stdout.write(f"     - {key}: {value}")
            else:
                self.stdout.write(f"[ERROR] {dashboard_data['error']}")
            
            self.stdout.write("[OK] Analytics dashboard test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Analytics test failed: {e}")
    
    def test_security(self):
        """Test advanced security features"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING ADVANCED SECURITY")
        self.stdout.write("=" * 60)
        
        try:
            # Test API key generation
            self.stdout.write("Testing API key generation...")
            api_key = generate_api_key("test")
            self.stdout.write(f"[OK] Generated API key: {api_key[:20]}...")
            
            # Test secure token generation
            self.stdout.write("\nTesting secure token generation...")
            token = security_utils.generate_secure_token(16)
            self.stdout.write(f"[OK] Generated secure token: {token}")
            
            # Test data obfuscation
            self.stdout.write("\nTesting data obfuscation...")
            test_data = "user@email.com"
            
            partial = security_utils.obfuscate_personal_data(test_data, "partial")
            full = security_utils.obfuscate_personal_data(test_data, "full")
            caesar = security_utils.obfuscate_personal_data(test_data, "caesar")
            
            self.stdout.write(f"     Original: {test_data}")
            self.stdout.write(f"     Partial:  {partial}")
            self.stdout.write(f"     Full:     {full}")
            self.stdout.write(f"     Caesar:   {caesar}")
            
            # Test audit hash
            self.stdout.write("\nTesting audit hash creation...")
            audit_data = {
                'user_id': 123,
                'action': 'login',
                'timestamp': '2025-01-09T12:00:00Z'
            }
            audit_hash = security_utils.create_audit_hash(audit_data)
            self.stdout.write(f"[OK] Audit hash: {audit_hash[:32]}...")
            
            # Test sensitive field hashing
            self.stdout.write("\nTesting sensitive field hashing...")
            test_field = "sensitive_data_123"
            hashed, salt = security_utils.hash_sensitive_field(test_field)
            verified = security_utils.verify_sensitive_field(test_field, hashed, salt)
            
            self.stdout.write(f"[OK] Hashed: {hashed[:20]}...")
            self.stdout.write(f"[OK] Salt: {salt}")
            self.stdout.write(f"[OK] Verification: {verified}")
            
            self.stdout.write("[OK] Advanced security test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Security test failed: {e}")
    
    def test_crypto(self, password=None):
        """Test cryptographic functions"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING CRYPTOGRAPHIC FUNCTIONS")
        self.stdout.write("=" * 60)
        
        try:
            # Test modern encryption
            if security_utils.modern_crypto.enabled:
                self.stdout.write("Testing modern encryption...")
                test_data = "This is sensitive information that needs encryption"
                
                encrypted = encrypt_data(test_data)
                if encrypted:
                    self.stdout.write(f"[OK] Encrypted data: {encrypted[:50]}...")
                    
                    decrypted = decrypt_data(encrypted)
                    if decrypted == test_data:
                        self.stdout.write("[OK] Decryption successful - data matches")
                    else:
                        self.stdout.write("[ERROR] Decryption failed - data mismatch")
                else:
                    self.stdout.write("[ERROR] Encryption failed")
            else:
                self.stdout.write("[WARNING] Modern cryptography not available")
            
            # Test password analysis
            if password:
                self.stdout.write(f"\nTesting password analysis for: '{password}'")
                analysis = analyze_password_strength(password)
                
                self.stdout.write(f"[OK] Password Analysis Results:")
                self.stdout.write(f"     Length: {analysis['length']}")
                self.stdout.write(f"     Strength Score: {analysis['strength_score']}/100")
                self.stdout.write(f"     Strength Level: {analysis['strength_level']}")
                self.stdout.write(f"     Entropy: {analysis['entropy']:.2f} bits")
                self.stdout.write(f"     Character Diversity: {analysis['character_diversity']}")
                
                if analysis['recommendations']:
                    self.stdout.write("     Recommendations:")
                    for rec in analysis['recommendations']:
                        self.stdout.write(f"     - {rec}")
            else:
                # Test with default password
                self.stdout.write("\nTesting password analysis with sample passwords...")
                test_passwords = ["123456", "Password123!", "Sup3r$3cur3P@ssw0rd2025"]
                
                for pwd in test_passwords:
                    analysis = analyze_password_strength(pwd)
                    self.stdout.write(f"     '{pwd}': {analysis['strength_level']} ({analysis['strength_score']}/100)")
            
            # Test advanced password hashing
            if security_utils.modern_crypto.enabled:
                self.stdout.write("\nTesting advanced password hashing...")
                test_pwd = password or "test_password_123"
                
                # Test Scrypt
                scrypt_hash = security_utils.modern_crypto.hash_password_advanced(test_pwd, "scrypt")
                if scrypt_hash:
                    self.stdout.write(f"[OK] Scrypt hash: {scrypt_hash[:50]}...")
                    
                    verified = security_utils.modern_crypto.verify_password_advanced(test_pwd, scrypt_hash)
                    self.stdout.write(f"[OK] Scrypt verification: {verified}")
                
                # Test PBKDF2
                pbkdf2_hash = security_utils.modern_crypto.hash_password_advanced(test_pwd, "pbkdf2")
                if pbkdf2_hash:
                    self.stdout.write(f"[OK] PBKDF2 hash: {pbkdf2_hash[:50]}...")
                    
                    verified = security_utils.modern_crypto.verify_password_advanced(test_pwd, pbkdf2_hash)
                    self.stdout.write(f"[OK] PBKDF2 verification: {verified}")
            
            self.stdout.write("[OK] Cryptographic functions test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Crypto test failed: {e}")
    
    def test_ciphers(self):
        """Test classical cipher algorithms"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING CLASSICAL CIPHER ALGORITHMS")
        self.stdout.write("=" * 60)
        
        try:
            test_text = "HELLO WORLD"
            ciphers = security_utils.cipher_algos
            
            # Test Caesar Cipher
            self.stdout.write("Testing Caesar Cipher...")
            caesar_encrypted = ciphers.caesar_cipher(test_text, 3)
            caesar_decrypted = ciphers.caesar_cipher(caesar_encrypted, 3, decrypt=True)
            
            self.stdout.write(f"     Original: {test_text}")
            self.stdout.write(f"     Encrypted: {caesar_encrypted}")
            self.stdout.write(f"     Decrypted: {caesar_decrypted}")
            self.stdout.write(f"     [OK] Match: {caesar_decrypted == test_text}")
            
            # Test Vigenere Cipher
            self.stdout.write("\nTesting Vigenere Cipher...")
            vigenere_key = "KEY"
            vigenere_encrypted = ciphers.vigenere_cipher(test_text, vigenere_key)
            vigenere_decrypted = ciphers.vigenere_cipher(vigenere_encrypted, vigenere_key, decrypt=True)
            
            self.stdout.write(f"     Original: {test_text}")
            self.stdout.write(f"     Key: {vigenere_key}")
            self.stdout.write(f"     Encrypted: {vigenere_encrypted}")
            self.stdout.write(f"     Decrypted: {vigenere_decrypted}")
            self.stdout.write(f"     [OK] Match: {vigenere_decrypted == test_text}")
            
            # Test Atbash Cipher
            self.stdout.write("\nTesting Atbash Cipher...")
            atbash_encrypted = ciphers.atbash_cipher(test_text)
            atbash_decrypted = ciphers.atbash_cipher(atbash_encrypted)  # Atbash is its own inverse
            
            self.stdout.write(f"     Original: {test_text}")
            self.stdout.write(f"     Encrypted: {atbash_encrypted}")
            self.stdout.write(f"     Decrypted: {atbash_decrypted}")
            self.stdout.write(f"     [OK] Match: {atbash_decrypted == test_text}")
            
            # Test Rail Fence Cipher
            self.stdout.write("\nTesting Rail Fence Cipher...")
            rail_key = 3
            rail_encrypted = ciphers.rail_fence_cipher(test_text, rail_key)
            rail_decrypted = ciphers.rail_fence_cipher(rail_encrypted, rail_key, decrypt=True)
            
            self.stdout.write(f"     Original: {test_text}")
            self.stdout.write(f"     Key (rails): {rail_key}")
            self.stdout.write(f"     Encrypted: {rail_encrypted}")
            self.stdout.write(f"     Decrypted: {rail_decrypted}")
            self.stdout.write(f"     [OK] Match: {rail_decrypted == test_text}")
            
            self.stdout.write("[OK] Classical ciphers test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Cipher test failed: {e}")
    
    def test_encryption(self, text):
        """Test encryption of provided text"""
        self.stdout.write(f"\nTesting encryption of: '{text}'")
        
        try:
            encrypted = encrypt_data(text)
            if encrypted:
                self.stdout.write(f"[OK] Encrypted: {encrypted}")
                
                decrypted = decrypt_data(encrypted)
                if decrypted:
                    self.stdout.write(f"[OK] Decrypted: {decrypted}")
                    self.stdout.write(f"[OK] Match: {decrypted == text}")
                else:
                    self.stdout.write("[ERROR] Decryption failed")
            else:
                self.stdout.write("[ERROR] Encryption failed")
                
        except Exception as e:
            self.stdout.write(f"[ERROR] Encryption test failed: {e}")
    
    def generate_dashboard(self):
        """Generate and display comprehensive dashboard"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("GENERATING COMPREHENSIVE DASHBOARD")
        self.stdout.write("=" * 60)
        
        try:
            dashboard_data = get_dashboard_data()
            
            if 'error' in dashboard_data:
                self.stdout.write(f"[ERROR] {dashboard_data['error']}")
                return
            
            self.stdout.write("[OK] Dashboard generated successfully!")
            
            # Display statistics
            stats = dashboard_data.get('statistics', {})
            if stats:
                self.stdout.write("\nSystem Statistics:")
                for key, value in stats.items():
                    self.stdout.write(f"  {key.replace('_', ' ').title()}: {value}")
            
            # Display chart availability
            charts = dashboard_data.get('charts', {})
            if charts:
                self.stdout.write("\nAvailable Charts:")
                for chart_name, chart_data in charts.items():
                    status = "[OK]" if chart_data else "[EMPTY]"
                    self.stdout.write(f"  {chart_name.replace('_', ' ').title()}: {status}")
            
            self.stdout.write(f"\nGenerated at: {dashboard_data.get('generated_at', 'Unknown')}")
            self.stdout.write("[OK] Dashboard generation completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Dashboard generation failed: {e}")