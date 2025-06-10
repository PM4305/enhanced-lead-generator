"""
Enhanced Lead Generation Tool with Playwright Integration
Author: Prakhar Madnani
Advanced web scraping for complex JavaScript-heavy websites
"""

import asyncio
from playwright.async_api import async_playwright
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Dict, List, Optional
import plotly.express as px
from email_validator import validate_email, EmailNotValidError
import time
from dataclasses import dataclass

@dataclass
class Lead:
    """Enhanced Lead data structure"""
    company_name: str
    domain: str
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    industry: str = ""
    employee_count: str = ""
    revenue_estimate: str = ""
    location: str = ""
    description: str = ""
    confidence_score: float = 0.0
    technology_stack: str = ""
    social_media: str = ""

class EnhancedLeadEnricher:
    """Advanced lead enrichment with Playwright for JavaScript-heavy sites"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.use_playwright = True  # Flag for complex sites
    
    async def extract_with_playwright(self, domain: str) -> Dict:
        """Advanced extraction using Playwright for JavaScript-heavy sites"""
        try:
            async with async_playwright() as p:
                # Launch browser with optimized settings
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = await context.new_page()
                
                # Navigate with timeout and wait for network idle
                url = f"https://{domain}" if not domain.startswith('http') else domain
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Extract comprehensive data
                data = await self._extract_advanced_data(page, domain)
                
                await browser.close()
                return data
                
        except Exception as e:
            st.warning(f"Playwright extraction failed for {domain}, falling back to BeautifulSoup: {str(e)}")
            return await self._fallback_extraction(domain)
    
    async def _extract_advanced_data(self, page, domain: str) -> Dict:
        """Extract comprehensive data using Playwright"""
        try:
            # Wait for dynamic content to load
            await page.wait_for_timeout(2000)
            
            # Extract basic information
            title = await page.title()
            content = await page.content()
            
            # Extract emails with JavaScript execution
            emails = await page.evaluate("""
                () => {
                    const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
                    const text = document.body.innerText;
                    const emails = text.match(emailRegex) || [];
                    return [...new Set(emails)].slice(0, 5);
                }
            """)
            
            # Extract phone numbers
            phones = await page.evaluate("""
                () => {
                    const phoneRegex = /(\+?\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}/g;
                    const text = document.body.innerText;
                    const phones = text.match(phoneRegex) || [];
                    return [...new Set(phones)].slice(0, 3);
                }
            """)
            
            # Extract social media links
            social_links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    const socialDomains = ['linkedin.com', 'twitter.com', 'facebook.com', 'instagram.com'];
                    const socialLinks = {};
                    
                    links.forEach(link => {
                        const href = link.href;
                        socialDomains.forEach(domain => {
                            if (href.includes(domain)) {
                                socialLinks[domain] = href;
                            }
                        });
                    });
                    
                    return socialLinks;
                }
            """)
            
            # Extract technology indicators
            tech_stack = await page.evaluate("""
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
                        if (src.includes('analytics')) technologies.push('Analytics');
                    });
                    
                    return [...new Set(technologies)];
                }
            """)
            
            # Parse with BeautifulSoup for additional extraction
            soup = BeautifulSoup(content, 'html.parser')
            
            return {
                'domain': domain,
                'title': self._clean_title(title),
                'description': self._extract_meta_description(soup),
                'emails': self._filter_emails(emails),
                'phones': phones[:2],
                'linkedin': social_links.get('linkedin.com', ''),
                'social_media': json.dumps(social_links),
                'technology_stack': ', '.join(tech_stack),
                'industry': self._classify_industry_advanced(content),
                'location': self._extract_location_advanced(content),
                'employee_count': self._estimate_company_size(content),
                'revenue_estimate': self._estimate_revenue(content)
            }
            
        except Exception as e:
            raise Exception(f"Advanced data extraction failed: {str(e)}")
    
    async def _fallback_extraction(self, domain: str) -> Dict:
        """Fallback to requests + BeautifulSoup"""
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
                'linkedin': self._extract_linkedin_basic(soup),
                'social_media': '{}',
                'technology_stack': '',
                'industry': self._classify_industry_basic(response.text),
                'location': '',
                'employee_count': '',
                'revenue_estimate': ''
            }
            
        except Exception as e:
            return {'domain': domain, 'error': str(e)}
    
    def _filter_emails(self, emails: List[str]) -> List[str]:
        """Filter and validate emails"""
        valid_emails = []
        for email in emails:
            try:
                validate_email(email)
                if not any(skip in email.lower() for skip in ['example', 'test', 'sample', 'noreply', 'support']):
                    valid_emails.append(email)
                    if len(valid_emails) >= 3:
                        break
            except EmailNotValidError:
                continue
        return valid_emails
    
    def _classify_industry_advanced(self, content: str) -> str:
        """Advanced industry classification with weighted keywords"""
        industry_keywords = {
            'SaaS/Software': {
                'primary': ['saas', 'software', 'platform', 'cloud', 'api'],
                'secondary': ['subscription', 'dashboard', 'integration', 'automation'],
                'weight': 1.5
            },
            'E-commerce': {
                'primary': ['shop', 'store', 'ecommerce', 'retail', 'marketplace'],
                'secondary': ['cart', 'checkout', 'product', 'buy', 'sell'],
                'weight': 1.3
            },
            'Fintech': {
                'primary': ['fintech', 'banking', 'payment', 'finance', 'crypto'],
                'secondary': ['transaction', 'wallet', 'investment', 'trading'],
                'weight': 1.4
            },
            'Healthcare': {
                'primary': ['health', 'medical', 'healthcare', 'telemedicine'],
                'secondary': ['patient', 'doctor', 'clinic', 'diagnosis'],
                'weight': 1.2
            },
            'AI/ML': {
                'primary': ['artificial intelligence', 'machine learning', 'ai', 'ml'],
                'secondary': ['neural', 'algorithm', 'data science', 'analytics'],
                'weight': 1.6
            }
        }
        
        content_lower = content.lower()
        industry_scores = {}
        
        for industry, data in industry_keywords.items():
            score = 0
            for keyword in data['primary']:
                score += content_lower.count(keyword) * 3
            for keyword in data['secondary']:
                score += content_lower.count(keyword) * 1
            
            if score > 0:
                industry_scores[industry] = score * data['weight']
        
        return max(industry_scores, key=industry_scores.get) if industry_scores else 'Other'
    
    def _estimate_company_size(self, content: str) -> str:
        """Estimate company size from content indicators"""
        content_lower = content.lower()
        
        large_indicators = ['fortune 500', 'enterprise', 'global', 'worldwide', 'international']
        medium_indicators = ['startup', 'growing', 'scale', 'expanding']
        small_indicators = ['small business', 'local', 'boutique', 'independent']
        
        large_score = sum(content_lower.count(indicator) for indicator in large_indicators)
        medium_score = sum(content_lower.count(indicator) for indicator in medium_indicators)
        small_score = sum(content_lower.count(indicator) for indicator in small_indicators)
        
        if large_score > medium_score and large_score > small_score:
            return "Large (1000+ employees)"
        elif medium_score > small_score:
            return "Medium (100-1000 employees)"
        elif small_score > 0:
            return "Small (10-100 employees)"
        else:
            return "Unknown"
    
    def _estimate_revenue(self, content: str) -> str:
        """Estimate revenue from content indicators"""
        content_lower = content.lower()
        
        if any(indicator in content_lower for indicator in ['billion', 'unicorn', 'ipo']):
            return "$1B+"
        elif any(indicator in content_lower for indicator in ['million', 'series', 'funded']):
            return "$10M-1B"
        elif any(indicator in content_lower for indicator in ['revenue', 'profitable', 'growing']):
            return "$1M-10M"
        else:
            return "Unknown"

class AdvancedLeadScorer:
    """Enhanced scoring with more sophisticated algorithms"""
    
    @staticmethod
    def calculate_advanced_score(lead_data: Dict) -> float:
        """Advanced confidence scoring with multiple factors"""
        score = 0.0
        
        # Email scoring (25 points)
        emails = lead_data.get('emails', [])
        if emails:
            score += min(len(emails) * 8, 25)
        
        # Phone scoring (15 points)
        if lead_data.get('phones'):
            score += 15
        
        # Social media presence (15 points)
        social_data = json.loads(lead_data.get('social_media', '{}'))
        score += min(len(social_data) * 5, 15)
        
        # Technology stack (10 points)
        if lead_data.get('technology_stack'):
            tech_count = len(lead_data['technology_stack'].split(','))
            score += min(tech_count * 2, 10)
        
        # Industry relevance (20 points)
        industry = lead_data.get('industry', '')
        if industry in ['SaaS/Software', 'Fintech', 'AI/ML']:
            score += 20
        elif industry in ['E-commerce', 'Healthcare']:
            score += 15
        elif industry != 'Other':
            score += 10
        
        # Company size (10 points)
        size = lead_data.get('employee_count', '')
        if 'Large' in size:
            score += 10
        elif 'Medium' in size:
            score += 7
        elif 'Small' in size:
            score += 5
        
        # Content quality (5 points)
        if lead_data.get('description') and len(lead_data['description']) > 100:
            score += 5
        
        return min(score, 100)

# Streamlit app integration would remain similar but with enhanced data processing
# The existing UI code can be updated to use these new classes

async def process_domain_enhanced(domain: str) -> Lead:
    """Process a single domain with enhanced extraction"""
    enricher = EnhancedLeadEnricher()
    scorer = AdvancedLeadScorer()
    
    # Extract data using Playwright
    data = await enricher.extract_with_playwright(domain)
    
    if 'error' not in data:
        # Calculate advanced score
        confidence = scorer.calculate_advanced_score(data)
        
        # Create lead object
        lead = Lead(
            company_name=data.get('title', domain),
            domain=domain,
            email=data.get('emails', [''])[0] if data.get('emails') else '',
            phone=data.get('phones', [''])[0] if data.get('phones') else '',
            linkedin=data.get('linkedin', ''),
            industry=data.get('industry', ''),
            employee_count=data.get('employee_count', ''),
            revenue_estimate=data.get('revenue_estimate', ''),
            location=data.get('location', ''),
            description=data.get('description', ''),
            confidence_score=confidence,
            technology_stack=data.get('technology_stack', ''),
            social_media=data.get('social_media', '{}')
        )
        
        return lead
    else:
        return Lead(
            company_name=domain,
            domain=domain,
            confidence_score=0.0
        )

# Usage example for integration
if __name__ == "__main__":
    async def test_enhanced_extraction():
        domain = "stripe.com"
        lead = await process_domain_enhanced(domain)
        print(f"Enhanced lead data for {domain}:")
        print(f"Company: {lead.company_name}")
        print(f"Confidence: {lead.confidence_score}%")
        print(f"Technology: {lead.technology_stack}")
    
    # asyncio.run(test_enhanced_extraction())