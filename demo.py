#!/usr/bin/env python3
"""
Enhanced Lead Generation Tool - Command Line Demo
Author: Prakhar Madnani
Demonstrates both standard and Playwright extraction capabilities
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
from typing import Dict, List
from email_validator import validate_email, EmailNotValidError

# Check for Playwright availability
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

class LeadGeneratorDemo:
    """Enhanced demo class showcasing dual extraction modes"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_company_info(self, domain: str, use_playwright: bool = False) -> Dict:
        """Extract company information with optional Playwright support"""
        print(f"🔍 Analyzing: {domain} ({'Playwright' if use_playwright else 'BeautifulSoup'})")
        
        if use_playwright and PLAYWRIGHT_AVAILABLE:
            return self._extract_with_playwright(domain)
        else:
            return self._extract_with_requests(domain)
    
    def _extract_with_playwright(self, domain: str) -> Dict:
        """Advanced extraction using Playwright"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                url = f"https://{domain}" if not domain.startswith('http') else domain
                page.goto(url, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(2000)  # Wait for dynamic content
                
                # Extract data using JavaScript
                title = page.title()
                content = page.content()
                
                # Extract emails using JavaScript execution
                emails = page.evaluate("""
                    () => {
                        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                        const text = document.body.innerText || '';
                        const emails = text.match(emailRegex) || [];
                        return [...new Set(emails)].slice(0, 5);
                    }
                """)
                
                # Extract phone numbers
                phones = page.evaluate("""
                    () => {
                        const phoneRegex = /(\\+?\\d{1,3}[-.]?)?\\(?\\d{3}\\)?[-.]?\\d{3}[-.]?\\d{4}/g;
                        const text = document.body.innerText || '';
                        const phones = text.match(phoneRegex) || [];
                        return [...new Set(phones)].slice(0, 3);
                    }
                """)
                
                # Extract technology stack
                tech_stack = page.evaluate("""
                    () => {
                        const scripts = Array.from(document.querySelectorAll('script[src]'));
                        const technologies = [];
                        
                        scripts.forEach(script => {
                            const src = script.src.toLowerCase();
                            if (src.includes('react')) technologies.push('React');
                            if (src.includes('angular')) technologies.push('Angular');
                            if (src.includes('vue')) technologies.push('Vue.js');
                            if (src.includes('jquery')) technologies.push('jQuery');
                            if (src.includes('bootstrap')) technologies.push('Bootstrap');
                        });
                        
                        return [...new Set(technologies)];
                    }
                """)
                
                browser.close()
                
                soup = BeautifulSoup(content, 'html.parser')
                
                return {
                    'domain': domain,
                    'title': self._clean_title(title),
                    'description': self._extract_meta_description(soup),
                    'emails': self._filter_emails(emails),
                    'phones': phones[:2],
                    'linkedin': self._extract_linkedin(soup),
                    'industry': self._classify_industry(content),
                    'location': self._extract_location(content),
                    'technology_stack': tech_stack,
                    'extraction_method': 'Playwright'
                }
                
        except Exception as e:
            print(f"❌ Playwright extraction failed: {str(e)}")
            return self._extract_with_requests(domain)
    
    def _extract_with_requests(self, domain: str) -> Dict:
        """Standard extraction using requests + BeautifulSoup"""
        try:
            url = f"https://{domain}" if not domain.startswith('http') else domain
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            return {
                'domain': domain,
                'title': self._clean_title(soup.title.string if soup.title else ""),
                'description': self._extract_meta_description(soup),
                'emails': self._extract_emails_basic(response.text),
                'phones': self._extract_phones_basic(response.text),
                'linkedin': self._extract_linkedin(soup),
                'industry': self._classify_industry(response.text),
                'location': self._extract_location(response.text),
                'technology_stack': [],
                'extraction_method': 'BeautifulSoup'
            }
            
        except Exception as e:
            return {'domain': domain, 'error': str(e)}
    
    def _clean_title(self, title: str) -> str:
        """Clean and extract company name from title"""
        if not title:
            return ""
        title = title.split('|')[0].split('-')[0].strip()
        return title[:100]
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content')[:200]
        return ''
    
    def _extract_emails_basic(self, text: str) -> List[str]:
        """Basic email extraction"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return self._filter_emails(emails)
    
    def _filter_emails(self, emails: List[str]) -> List[str]:
        """Filter and validate emails"""
        valid_emails = []
        for email in set(emails):
            try:
                validate_email(email)
                if not any(skip in email.lower() for skip in ['example', 'test', 'sample', 'noreply', 'support']):
                    valid_emails.append(email)
                    if len(valid_emails) >= 3:
                        break
            except EmailNotValidError:
                continue
        return valid_emails
    
    def _extract_phones_basic(self, text: str) -> List[str]:
        """Basic phone extraction"""
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',
            r'\b\+\d{1,3}[-.]?\d{3,4}[-.]?\d{3,4}[-.]?\d{3,4}\b'
        ]
        
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
            if len(phones) >= 2:
                break
        
        return list(set(phones))[:2]
    
    def _extract_linkedin(self, soup: BeautifulSoup) -> str:
        """Extract LinkedIn company page"""
        linkedin_links = soup.find_all('a', href=re.compile(r'linkedin\.com/company'))
        return linkedin_links[0].get('href', '') if linkedin_links else ''
    
    def _classify_industry(self, text: str) -> str:
        """Advanced industry classification"""
        industry_keywords = {
            'SaaS/Software': ['saas', 'software', 'platform', 'cloud', 'api', 'app', 'tech'],
            'E-commerce': ['shop', 'store', 'ecommerce', 'retail', 'marketplace', 'buy', 'sell'],
            'Fintech': ['fintech', 'banking', 'payment', 'finance', 'crypto', 'trading'],
            'Healthcare': ['health', 'medical', 'healthcare', 'telemedicine', 'patient'],
            'Communication': ['communication', 'messaging', 'chat', 'video', 'conference'],
            'Productivity': ['productivity', 'workspace', 'collaboration', 'notes', 'project'],
            'Marketing': ['marketing', 'advertising', 'seo', 'social media', 'analytics'],
            'Developer Tools': ['developer', 'code', 'github', 'repository', 'programming']
        }
        
        text_lower = text.lower()
        industry_scores = {}
        
        for industry, keywords in industry_keywords.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            if score > 0:
                industry_scores[industry] = score
        
        return max(industry_scores, key=industry_scores.get) if industry_scores else 'Other'
    
    def _extract_location(self, text: str) -> str:
        """Extract company location"""
        location_patterns = [
            r'(?:located in|based in|headquarters in)\s+([A-Z][a-z]+(?:,\s*[A-Z]{2})?)',
            r'([A-Z][a-z]+,\s*[A-Z]{2})\s*\d{5}',
            r'([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)\s*office'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0] if isinstance(matches[0], str) else matches[0][0]
        
        return ''
    
    def _calculate_confidence(self, info: Dict) -> float:
        """Calculate confidence score"""
        score = 0.0
        
        # Email availability (30 points)
        if info.get('emails'):
            score += min(len(info['emails']) * 10, 30)
        
        # Phone availability (20 points)
        if info.get('phones'):
            score += 20
        
        # LinkedIn presence (15 points)
        if info.get('linkedin'):
            score += 15
        
        # Industry classification (15 points)
        if info.get('industry') and info['industry'] != 'Other':
            score += 15
        
        # Technology stack (10 points)
        if info.get('technology_stack') and len(info['technology_stack']) > 0:
            score += 10
        
        # Description quality (10 points)
        if info.get('description') and len(info['description']) > 50:
            score += 10
        
        return min(score, 100)
    
    def demo_single_domain(self, domain: str, use_playwright: bool = False):
        """Demonstrate single domain analysis"""
        method = "Playwright" if use_playwright else "BeautifulSoup"
        print(f"\n{'='*70}")
        print(f"🎯 ENHANCED LEAD ANALYSIS DEMO - {method} Mode")
        print(f"{'='*70}")
        
        start_time = time.time()
        result = self.extract_company_info(domain, use_playwright)
        processing_time = time.time() - start_time
        
        if 'error' not in result:
            confidence = self._calculate_confidence(result)
            
            print(f"✅ Successfully analyzed: {domain}")
            print(f"⏱️  Processing time: {processing_time:.2f} seconds")
            print(f"🔧 Extraction method: {result.get('extraction_method', 'Unknown')}")
            print(f"\n📊 RESULTS:")
            print(f"   Company: {result.get('title', 'N/A')}")
            print(f"   Industry: {result.get('industry', 'N/A')}")
            print(f"   Emails: {', '.join(result.get('emails', [])) or 'None found'}")
            print(f"   Phones: {', '.join(result.get('phones', [])) or 'None found'}")
            print(f"   LinkedIn: {'✅' if result.get('linkedin') else '❌'}")
            print(f"   Location: {result.get('location', 'N/A')}")
            
            # Show technology stack if available
            tech_stack = result.get('technology_stack', [])
            if tech_stack:
                print(f"   Technology: {', '.join(tech_stack)}")
            
            print(f"   Confidence: {confidence:.1f}%")
            
            if result.get('description'):
                print(f"   Description: {result['description'][:100]}...")
        else:
            print(f"❌ Failed to analyze: {domain}")
            print(f"   Error: {result.get('error', 'Unknown error')}")
    
    def demo_comparison(self, domain: str):
        """Compare standard vs enhanced extraction"""
        print(f"\n{'='*70}")
        print(f"🔄 EXTRACTION METHOD COMPARISON")
        print(f"{'='*70}")
        print(f"Testing domain: {domain}")
        
        # Standard extraction
        print(f"\n1️⃣ STANDARD MODE (BeautifulSoup)")
        print("-" * 40)
        start_time = time.time()
        standard_result = self.extract_company_info(domain, use_playwright=False)
        standard_time = time.time() - start_time
        
        # Enhanced extraction (if available)
        if PLAYWRIGHT_AVAILABLE:
            print(f"\n2️⃣ ENHANCED MODE (Playwright)")
            print("-" * 40)
            start_time = time.time()
            enhanced_result = self.extract_company_info(domain, use_playwright=True)
            enhanced_time = time.time() - start_time
        else:
            print(f"\n2️⃣ ENHANCED MODE (Playwright)")
            print("-" * 40)
            print("❌ Playwright not available. Install with: pip install playwright")
            enhanced_result = None
            enhanced_time = 0
        
        # Comparison results
        print(f"\n📊 COMPARISON RESULTS:")
        print(f"{'Metric':<20} {'Standard':<15} {'Enhanced':<15} {'Winner':<10}")
        print("-" * 65)
        
        std_emails = len(standard_result.get('emails', []))
        enh_emails = len(enhanced_result.get('emails', [])) if enhanced_result else 0
        emails_winner = "Enhanced" if enh_emails > std_emails else "Standard" if std_emails > enh_emails else "Tie"
        print(f"{'Emails Found':<20} {std_emails:<15} {enh_emails:<15} {emails_winner:<10}")
        
        std_phones = len(standard_result.get('phones', []))
        enh_phones = len(enhanced_result.get('phones', [])) if enhanced_result else 0
        phones_winner = "Enhanced" if enh_phones > std_phones else "Standard" if std_phones > enh_phones else "Tie"
        print(f"{'Phones Found':<20} {std_phones:<15} {enh_phones:<15} {phones_winner:<10}")
        
        std_tech = len(standard_result.get('technology_stack', []))
        enh_tech = len(enhanced_result.get('technology_stack', [])) if enhanced_result else 0
        tech_winner = "Enhanced" if enh_tech > std_tech else "Standard" if std_tech > enh_tech else "Tie"
        print(f"{'Tech Stack Items':<20} {std_tech:<15} {enh_tech:<15} {tech_winner:<10}")
        
        time_winner = "Standard" if standard_time < enhanced_time else "Enhanced"
        print(f"{'Processing Time':<20} {standard_time:.2f}s{'':<10} {enhanced_time:.2f}s{'':<10} {time_winner:<10}")
        
    def demo_batch_processing(self, domains: List[str]):
        """Demonstrate batch processing capabilities"""
        print(f"\n{'='*70}")
        print(f"🚀 BATCH PROCESSING DEMO")
        print(f"{'='*70}")
        print(f"Processing {len(domains)} domains...\n")
        
        results = []
        extraction_stats = {'standard': 0, 'enhanced': 0, 'errors': 0}
        
        for i, domain in enumerate(domains, 1):
            print(f"[{i}/{len(domains)}] Processing {domain}...")
            
            # Use Playwright for modern domains, standard for others
            use_playwright = domain in ['stripe.com', 'notion.so', 'figma.com', 'linear.app']
            
            try:
                result = self.extract_company_info(domain, use_playwright)
                if 'error' not in result:
                    result['confidence_score'] = self._calculate_confidence(result)
                    results.append(result)
                    
                    method = result.get('extraction_method', 'BeautifulSoup')
                    if method == 'Playwright':
                        extraction_stats['enhanced'] += 1
                    else:
                        extraction_stats['standard'] += 1
                else:
                    extraction_stats['errors'] += 1
            except Exception as e:
                extraction_stats['errors'] += 1
                print(f"   ❌ Error: {str(e)}")
        
        # Summary statistics
        successful = [r for r in results if 'error' not in r]
        with_email = [r for r in successful if r.get('emails')]
        with_phone = [r for r in successful if r.get('phones')]
        high_confidence = [r for r in successful if r.get('confidence_score', 0) >= 70]
        
        print(f"\n📈 BATCH PROCESSING RESULTS:")
        print(f"   Total Processed: {len(domains)}")
        print(f"   Successful: {len(successful)} ({len(successful)/len(domains)*100:.1f}%)")
        print(f"   With Email: {len(with_email)} ({len(with_email)/len(domains)*100:.1f}%)")
        print(f"   With Phone: {len(with_phone)} ({len(with_phone)/len(domains)*100:.1f}%)")
        print(f"   High Confidence (70%+): {len(high_confidence)} ({len(high_confidence)/len(domains)*100:.1f}%)")
        
        print(f"\n🔧 EXTRACTION METHOD BREAKDOWN:")
        print(f"   Standard (BeautifulSoup): {extraction_stats['standard']}")
        print(f"   Enhanced (Playwright): {extraction_stats['enhanced']}")
        print(f"   Errors: {extraction_stats['errors']}")
        
        if successful:
            avg_confidence = sum(r.get('confidence_score', 0) for r in successful) / len(successful)
            print(f"   Average Confidence: {avg_confidence:.1f}%")
        
        # Show top results
        print(f"\n🏆 TOP QUALIFIED LEADS:")
        top_leads = sorted(successful, key=lambda x: x.get('confidence_score', 0), reverse=True)[:3]
        
        for i, lead in enumerate(top_leads, 1):
            print(f"   {i}. {lead.get('title', lead['domain'])} ({lead.get('confidence_score', 0):.1f}%)")
            if lead.get('emails'):
                print(f"      📧 {lead['emails'][0]}")
            if lead.get('industry'):
                print(f"      🏢 {lead['industry']}")
            if lead.get('technology_stack'):
                tech_list = lead['technology_stack']
                if isinstance(tech_list, list) and tech_list:
                    print(f"      💻 {', '.join(tech_list)}")
        
        return results

def main():
    """Main demo function"""
    print("🎯 Enhanced Lead Generation Tool - Command Line Demo")
    print("Author: Prakhar Madnani | Built for Caprae Capital Challenge")
    print("=" * 70)
    
    demo = LeadGeneratorDemo()
    
    if not PLAYWRIGHT_AVAILABLE:
        print("⚠️  Note: Playwright not installed. Enhanced features will be limited.")
        print("   Install with: pip install playwright && playwright install chromium")
        print()
    
    # Demo 1: Single domain analysis (Standard)
    print("Demo 1: Standard Extraction")
    demo.demo_single_domain("github.com", use_playwright=False)
    
    # Demo 2: Single domain analysis (Enhanced, if available)
    if PLAYWRIGHT_AVAILABLE:
        print("\nDemo 2: Enhanced Extraction")
        demo.demo_single_domain("stripe.com", use_playwright=True)
        
        # Demo 3: Comparison
        print("\nDemo 3: Method Comparison")
        demo.demo_comparison("notion.so")
    
    # Demo 4: Batch processing
    print("\nDemo 4: Batch Processing")
    sample_domains = [
        "stripe.com",      # Fintech with heavy JS
        "github.com",      # Developer tools
        "zoom.us",         # Communication SaaS
        "shopify.com",     # E-commerce platform
        "notion.so"        # Productivity tool
    ]
    
    results = demo.demo_batch_processing(sample_domains)
    
    # Demo 5: Export simulation
    print(f"\n{'='*70}")
    print("💾 EXPORT SIMULATION")
    print("="*70)
    
    if results:
        export_data = []
        for result in results:
            if 'error' not in result:
                export_data.append({
                    'Company': result.get('title', result['domain']),
                    'Domain': result['domain'],
                    'Email': result.get('emails', [''])[0],
                    'Phone': result.get('phones', [''])[0],
                    'Industry': result.get('industry', ''),
                    'Technology': ', '.join(result.get('technology_stack', [])) if isinstance(result.get('technology_stack'), list) else '',
                    'Confidence': f"{result.get('confidence_score', 0):.1f}%",
                    'Method': result.get('extraction_method', 'Unknown')
                })
        
        print("📊 Sample export data (JSON format):")
        print(json.dumps(export_data[:2], indent=2))
        print(f"\n✅ Ready to export {len(export_data)} qualified leads")
    
    print(f"\n{'='*70}")
    print("🎉 Demo completed successfully!")
    print("💡 Run 'streamlit run lead_generator.py' for full UI experience")
    print("🚀 Enable Playwright mode in sidebar for enhanced extraction")
    print("="*70)

if __name__ == "__main__":
    main()