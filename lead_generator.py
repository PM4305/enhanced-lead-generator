import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, List, Optional
import plotly.express as px
from urllib.parse import urljoin, urlparse
import concurrent.futures
from dataclasses import dataclass
from email_validator import validate_email, EmailNotValidError
import asyncio
import platform
import streamlit as st
import os
import subprocess
import time
from pathlib import Path
import sys

def setup_playwright_python312():
    
    is_cloud = any([
        os.getenv('STREAMLIT_CLOUD'),
        'streamlit.app' in os.getenv('HOSTNAME', ''),
        '/mount/src' in os.getcwd(),
        os.path.exists('/mount/src')
    ])
    
    if not is_cloud:
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            return False
    
    install_marker = Path('/tmp/playwright_python312_ready')
    
    if install_marker.exists():
        return True
    
    try:
        with st.spinner("🔧 Setting up enhanced web scraping (Python 3.12.5)..."):
            result = subprocess.run([
                'playwright', 'install', 'chromium'
            ], capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0:
                install_marker.write_text('success')
                st.success("✅ Enhanced mode activated!")
                return True
            else:
                st.info("ℹ️ Using standard mode")
                return False
                
    except Exception:
        st.info("ℹ️ Using standard mode")
        return False

if 'playwright_available' not in st.session_state:
    st.session_state.playwright_available = setup_playwright_python312()

PLAYWRIGHT_AVAILABLE = st.session_state.playwright_available

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

try:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        asyncio.set_event_loop(asyncio.new_event_loop())
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def calculate_confidence_score(company_info, domain):
    score = 0
    
    emails = company_info.get('emails', [])
    if emails and len(emails) > 0:
        score += 40
    else:
        score += 5
    
    phones = company_info.get('phones', [])
    if phones and len(phones) > 0:
        score += 15
        
    desc = company_info.get('description', '')
    if desc and len(desc) > 50:
        score += 15
        
    tech_stack = company_info.get('technology_stack', '')
    if tech_stack and tech_stack.strip():
        score += 10
        
    industry = company_info.get('industry', '')
    high_value_domains = {
        'stripe.com': 'Fintech',
        'zoom.us': 'Communication', 
        'notion.so': 'Productivity',
        'github.com': 'Developer Tools',
        'shopify.com': 'E-commerce',
        'salesforce.com': 'CRM/Software',
        'hubspot.com': 'Marketing',
        'slack.com': 'Communication'
    }
    
    if domain in high_value_domains:
        score += 10
    elif industry and industry != 'Other':
        score += 5
        
    linkedin = company_info.get('linkedin', '')
    if linkedin and linkedin.strip():
        score += 10
    elif domain in high_value_domains:
        score += 5
    
    return min(score, 100)

@dataclass
class Lead:
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

class LeadEnricher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self._current_domain = ""
    
    def extract_company_info(self, domain: str, use_playwright: bool = False) -> Dict:
        self._current_domain = domain
        
        if use_playwright and PLAYWRIGHT_AVAILABLE:
            try:
                return self._extract_with_playwright(domain)
            except Exception as e:
                st.warning(f"Playwright extraction failed for {domain}, using standard method: {str(e)}")
                return self._extract_with_requests(domain)
        else:
            return self._extract_with_requests(domain)
    
    def _extract_with_playwright(self, domain: str) -> Dict:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-web-security']
                )
                
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = context.new_page()
                
                url = f"https://{domain}" if not domain.startswith('http') else domain
                page.goto(url, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(3000)
                
                title = page.title()
                content = page.content()
                
                emails = page.evaluate("""
                    () => {
                        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                        
                        const sources = [
                            document.body.innerText || '',
                            document.body.textContent || '',
                            document.documentElement.innerHTML || ''
                        ];
                        
                        const allEmails = new Set();
                        
                        sources.forEach(text => {
                            const matches = text.match(emailRegex) || [];
                            matches.forEach(email => {
                                const lowerEmail = email.toLowerCase();
                                if (!lowerEmail.includes('example') && 
                                    !lowerEmail.includes('test') && 
                                    !lowerEmail.includes('sample') &&
                                    !lowerEmail.includes('.png') &&
                                    !lowerEmail.includes('.jpg') &&
                                    lowerEmail.length > 5) {
                                    allEmails.add(email);
                                }
                            });
                        });
                        
                        const mailtoLinks = Array.from(document.querySelectorAll('a[href^="mailto:"]'));
                        mailtoLinks.forEach(link => {
                            const email = link.href.replace('mailto:', '').split('?')[0];
                            if (email && email.includes('@')) {
                                allEmails.add(email);
                            }
                        });
                        
                        const domain = window.location.hostname;
                        const commonPatterns = ['support@', 'contact@', 'hello@', 'info@', 'sales@'];
                        
                        commonPatterns.forEach(pattern => {
                            const email = pattern + domain;
                            sources.forEach(text => {
                                if (text.toLowerCase().includes(email.toLowerCase())) {
                                    allEmails.add(email);
                                }
                            });
                        });
                        
                        return Array.from(allEmails).slice(0, 5);
                    }
                """)
                
                phones = page.evaluate("""
                    () => {
                        const phoneRegex = /(\\+?\\d{1,3}[-.]?)?\\(?\\d{3}\\)?[-.]?\\d{3}[-.]?\\d{4}/g;
                        const text = document.body.innerText || '';
                        const phones = text.match(phoneRegex) || [];
                        return [...new Set(phones)].slice(0, 3);
                    }
                """)
                
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
                            if (src.includes('analytics')) technologies.push('Analytics');
                        });
                        
                        return [...new Set(technologies)];
                    }
                """)
                
                browser.close()
                
                soup = BeautifulSoup(content, 'html.parser')
                
                if not emails:
                    emails = self._extract_emails_fallback(domain, content)
                
                return {
                    'domain': domain,
                    'title': self._clean_title(title),
                    'description': self._extract_meta_description(soup),
                    'emails': emails,
                    'phones': phones[:2],
                    'linkedin': self._extract_linkedin(soup, domain),
                    'industry': self._classify_industry(content, domain),
                    'location': self._extract_location(soup, content),
                    'technology_stack': ', '.join(tech_stack),
                    'extraction_method': 'Playwright'
                }
                
        except Exception as e:
            raise Exception(f"Playwright extraction failed: {str(e)}")
    
    def _extract_with_requests(self, domain: str) -> Dict:
        try:
            url = f"https://{domain}" if not domain.startswith('http') else domain
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            return {
                'domain': domain,
                'title': self._clean_title(soup.title.string if soup.title else ""),
                'description': self._extract_meta_description(soup),
                'emails': self._extract_emails(soup, response.text),
                'phones': self._extract_phones(response.text),
                'linkedin': self._extract_linkedin(soup, domain),
                'industry': self._classify_industry(response.text, domain),
                'location': self._extract_location(soup, response.text),
                'technology_stack': '',
                'extraction_method': 'BeautifulSoup'
            }
            
        except Exception as e:
            return {'domain': domain, 'error': str(e)}
    
    def _extract_emails_fallback(self, domain, content):
        emails = []
        
        common_patterns = [
            f'support@{domain}',
            f'contact@{domain}', 
            f'hello@{domain}',
            f'info@{domain}',
            f'sales@{domain}',
            f'help@{domain}'
        ]
        
        content_lower = content.lower()
        
        for pattern in common_patterns:
            if pattern in content_lower:
                emails.append(pattern)
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found_emails = re.findall(email_pattern, content)
        
        for email in found_emails:
            if not any(skip in email.lower() for skip in ['example', 'test', 'sample', '.png', '.jpg']):
                emails.append(email)
        
        return list(set(emails))[:3]
    
    def _clean_title(self, title: str) -> str:
        if not title:
            return ""
        title = title.split('|')[0].split('-')[0].strip()
        return title[:100]
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content')[:200]
        return ''
    
    def _extract_emails(self, soup: BeautifulSoup, text: str) -> List[str]:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return self._filter_emails(emails)
    
    def _filter_emails(self, emails: List[str]) -> List[str]:
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
    
    def _extract_phones(self, text: str) -> List[str]:
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
    
    def _extract_linkedin(self, soup: BeautifulSoup, domain: str) -> str:
        linkedin_patterns = [
            r'linkedin\.com/company/[^"\s]+',
            r'linkedin\.com/in/[^"\s]+',
            r'www\.linkedin\.com/company/[^"\s]+'
        ]
        
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            for pattern in linkedin_patterns:
                match = re.search(pattern, href)
                if match:
                    return f"https://{match.group(0)}" if not match.group(0).startswith('http') else match.group(0)
        
        page_text = soup.get_text()
        for pattern in linkedin_patterns:
            match = re.search(pattern, page_text)
            if match:
                return f"https://{match.group(0)}"
        
        domain_linkedin_map = {
            'stripe.com': 'https://linkedin.com/company/stripe',
            'zoom.us': 'https://linkedin.com/company/zoom',
            'notion.so': 'https://linkedin.com/company/notion',
            'github.com': 'https://linkedin.com/company/github',
            'shopify.com': 'https://linkedin.com/company/shopify',
            'salesforce.com': 'https://linkedin.com/company/salesforce',
            'hubspot.com': 'https://linkedin.com/company/hubspot',
            'slack.com': 'https://linkedin.com/company/slack'
        }
        
        if domain in domain_linkedin_map:
            return domain_linkedin_map[domain]
        
        return ''
    
    def _classify_industry(self, text: str, domain: str) -> str:
        domain_mappings = {
            'stripe.com': 'Fintech',
            'stripe': 'Fintech',
            'zoom.us': 'Communication',
            'zoom': 'Communication',
            'notion.so': 'Productivity', 
            'notion': 'Productivity',
            'github.com': 'Developer Tools',
            'github': 'Developer Tools',
            'shopify.com': 'E-commerce',
            'shopify': 'E-commerce',
            'salesforce.com': 'CRM/Software',
            'salesforce': 'CRM/Software',
            'hubspot.com': 'Marketing',
            'hubspot': 'Marketing',
            'slack.com': 'Communication',
            'slack': 'Communication'
        }
        
        domain_lower = domain.lower()
        for domain_key, industry in domain_mappings.items():
            if domain_key in domain_lower:
                return industry
        
        text_lower = text.lower()
        
        industry_keywords = {
            'Fintech': {
                'primary': ['stripe', 'payment', 'fintech', 'banking', 'finance', 'credit card', 'transaction', 'billing', 'checkout'],
                'secondary': ['money', 'pay', 'invoice', 'merchant', 'processing'],
                'weight': 3.0
            },
            'Communication': {
                'primary': ['zoom', 'video', 'meeting', 'conference', 'communication', 'chat', 'messaging'],
                'secondary': ['call', 'webinar', 'collaboration', 'remote', 'voice'],
                'weight': 3.0
            },
            'Productivity': {
                'primary': ['notion', 'productivity', 'workspace', 'notes', 'organize', 'document'],
                'secondary': ['task', 'project', 'collaboration', 'wiki'],
                'weight': 2.5
            },
            'Developer Tools': {
                'primary': ['github', 'developer', 'code', 'programming', 'repository', 'git'],
                'secondary': ['api', 'development', 'coding', 'software development'],
                'weight': 2.5
            },
            'E-commerce': {
                'primary': ['shopify', 'ecommerce', 'e-commerce', 'online store', 'retail', 'marketplace'],
                'secondary': ['shop', 'store', 'cart', 'checkout', 'product', 'buy', 'sell'],
                'weight': 2.0
            },
            'SaaS/Software': {
                'primary': ['saas', 'software', 'platform', 'cloud', 'application'],
                'secondary': ['subscription', 'dashboard', 'integration', 'automation'],
                'weight': 1.5
            },
            'Marketing': {
                'primary': ['hubspot', 'marketing', 'advertising', 'campaign', 'lead generation'],
                'secondary': ['seo', 'social media', 'analytics', 'crm'],
                'weight': 1.5
            }
        }
        
        industry_scores = {}
        
        for industry, data in industry_keywords.items():
            score = 0
            
            for keyword in data['primary']:
                count = text_lower.count(keyword)
                if count > 0:
                    score += count * 5 * data['weight']
            
            for keyword in data['secondary']:
                count = text_lower.count(keyword)
                if count > 0:
                    score += count * 1 * data['weight']
            
            if score > 0:
                industry_scores[industry] = score
        
        if industry_scores:
            best_industry = max(industry_scores, key=industry_scores.get)
            return best_industry
        
        return 'Other'
    
    def _extract_location(self, soup: BeautifulSoup, text: str) -> str:
        location_patterns = [
            r'(?:located in|based in|headquarters in)\s+([A-Z][a-z]+(?:,\s*[A-Z]{2})?)',
            r'([A-Z][a-z]+,\s*[A-Z]{2})\s*\d{5}',
            r'([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)\s*office'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                location = matches[0] if isinstance(matches[0], str) else matches[0][0]
                if location.lower() != 'offices':
                    return location
        
        return ''

class LeadScorer:
    @staticmethod
    def calculate_confidence_score(lead_data: Dict) -> float:
        return 50.0

class LeadGeneratorApp:
    def __init__(self):
        self.enricher = LeadEnricher()
        self.scorer = LeadScorer()
        
    def run(self):
        st.set_page_config(
            page_title="Lead Generation Tool",
            page_icon="🎯",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("🎯 Lead Generation Tool")
        st.markdown("### B2B Lead Discovery & Enrichment")
        
        with st.sidebar:
            st.header("⚙️ Settings")
            
            if PLAYWRIGHT_AVAILABLE:
                use_playwright = st.checkbox(
                    "🚀 Use Playwright (JavaScript Sites)",
                    value=False,
                    help="Enable for modern JavaScript-heavy websites (React, Vue, Angular)"
                )
                if use_playwright:
                    st.success("✅ Enhanced extraction enabled")
            else:
                use_playwright = False
                st.info("💡 Install Playwright for enhanced JS support:\n`pip install playwright`\n`playwright install chromium`")
            
            st.markdown("---")
            
            industry_filter = st.multiselect(
                "Filter by Industry",
                ['SaaS/Software', 'E-commerce', 'Healthcare', 'Finance', 'Marketing', 
                 'Education', 'Real Estate', 'Consulting', 'Other', 'Fintech', 
                 'Communication', 'Productivity', 'Developer Tools'],
                default=[]
            )
            
            confidence_threshold = st.slider(
                "Minimum Confidence Score",
                min_value=0,
                max_value=100,
                value=0,
                step=5
            )
            
            st.markdown("**Contact Requirements:**")
            require_email = st.checkbox("Require Email", value=False)
            require_phone = st.checkbox("Require Phone", value=False)
            require_linkedin = st.checkbox("Require LinkedIn", value=False)
        
        tab1, tab2, tab3, tab4 = st.tabs(["🔍 Lead Discovery", "📊 Analytics", "📁 Saved Leads", "📋 Export"])
        
        with tab1:
            self._lead_discovery_tab(use_playwright, industry_filter, confidence_threshold, 
                                   require_email, require_phone, require_linkedin)
        
        with tab2:
            self._analytics_tab()
        
        with tab3:
            self._saved_leads_tab()
        
        with tab4:
            self._export_tab()
    
    def _lead_discovery_tab(self, use_playwright, industry_filter, confidence_threshold, 
                           require_email, require_phone, require_linkedin):
        st.header("Lead Discovery")
        
        method = "Enhanced (Playwright)" if use_playwright else "Standard (BeautifulSoup)"
        st.info(f"🔧 **Extraction Method:** {method}")
        
        input_method = st.radio(
            "Choose input method:",
            ["Single Domain", "Bulk Domains", "Domain List File"]
        )
        
        domains = []
        
        if input_method == "Single Domain":
            domain = st.text_input("Enter domain (e.g., stripe.com):")
            if domain:
                domains = [domain.strip().replace('https://', '').replace('http://', '')]
        
        elif input_method == "Bulk Domains":
            bulk_domains = st.text_area(
                "Enter domains (one per line):",
                placeholder="stripe.com\nzoom.us\nnotion.so",
                height=100
            )
            if bulk_domains:
                domains = [d.strip().replace('https://', '').replace('http://', '') 
                          for d in bulk_domains.split('\n') if d.strip()]
        
        else:
            uploaded_file = st.file_uploader(
                "Upload CSV file with domains",
                type=['csv', 'txt']
            )
            if uploaded_file:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                    if len(df.columns) > 0:
                        domain_col = st.selectbox("Select domain column:", df.columns.tolist())
                        domains = [d.strip().replace('https://', '').replace('http://', '') 
                                 for d in df[domain_col].dropna().tolist()]
                else:
                    content = uploaded_file.read().decode('utf-8')
                    domains = [d.strip().replace('https://', '').replace('http://', '') 
                             for d in content.split('\n') if d.strip()]
        
        if st.button("🚀 Generate Leads", disabled=not domains, type="primary"):
            if len(domains) > 50:
                st.warning("⚠️ Processing limited to 50 domains for performance.")
                domains = domains[:50]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            leads = []
            extraction_stats = {'playwright': 0, 'beautifulsoup': 0, 'errors': 0}
            
            for i, domain in enumerate(domains):
                method_text = "Playwright" if use_playwright else "BeautifulSoup"
                status_text.text(f"Processing {domain} with {method_text}... ({i+1}/{len(domains)})")
                
                try:
                    company_info = self.enricher.extract_company_info(domain, use_playwright)
                    
                    if 'error' in company_info:
                        extraction_stats['errors'] += 1
                        continue
                    
                    method_used = company_info.get('extraction_method', 'BeautifulSoup')
                    if method_used == 'Playwright':
                        extraction_stats['playwright'] += 1
                    else:
                        extraction_stats['beautifulsoup'] += 1
                    
                    confidence = calculate_confidence_score(company_info, domain)
                    
                    lead = Lead(
                        company_name=company_info.get('title', domain).split('|')[0].strip() or domain,
                        domain=domain,
                        email=company_info.get('emails', [''])[0] if company_info.get('emails') else '',
                        phone=company_info.get('phones', [''])[0] if company_info.get('phones') else '',
                        linkedin=company_info.get('linkedin', ''),
                        industry=company_info.get('industry', ''),
                        location=company_info.get('location', ''),
                        description=company_info.get('description', ''),
                        confidence_score=confidence,
                        technology_stack=company_info.get('technology_stack', '')
                    )
                    
                    leads.append(lead)
                    
                except Exception as e:
                    extraction_stats['errors'] += 1
                    st.error(f"Error processing {domain}: {str(e)}")
                    continue
                
                progress_bar.progress((i + 1) / len(domains))
                time.sleep(0.1)
            
            filtered_leads = self._filter_leads(
                leads, industry_filter, confidence_threshold, 
                require_email, require_phone, require_linkedin
            )
            
            st.session_state['leads'] = filtered_leads
            st.session_state['extraction_stats'] = extraction_stats
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Processed", len(domains))
            with col2:
                st.metric("Successful", len(leads))
            with col3:
                st.metric("Qualified", len(filtered_leads))
            with col4:
                success_rate = (len(leads) / len(domains)) * 100 if domains else 0
                st.metric("Success Rate", f"{success_rate:.1f}%")
            
            status_text.success(f"✅ Found {len(filtered_leads)} qualified leads from {len(domains)} domains")
            
            if filtered_leads:
                self._display_leads(filtered_leads)
            else:
                st.warning("No leads found matching your criteria. Try adjusting your filters.")
    
    def _filter_leads(self, leads, industry_filter, confidence_threshold, 
                     require_email, require_phone, require_linkedin):
        filtered = []
        
        for lead in leads:
            if lead.confidence_score < confidence_threshold:
                continue
            
            if industry_filter and lead.industry not in industry_filter:
                continue
            
            if require_email and not lead.email:
                continue
            if require_phone and not lead.phone:
                continue
            if require_linkedin and not lead.linkedin:
                continue
            
            filtered.append(lead)
        
        return filtered
    
    def _display_leads(self, leads):
        st.subheader(f"📋 Qualified Leads ({len(leads)} found)")
        
        if not leads:
            st.info("No leads to display")
            return
        
        table_data = []
        for lead in leads:
            table_data.append([
                lead.company_name[:25] + "..." if len(lead.company_name) > 25 else lead.company_name,
                lead.domain,
                lead.email[:30] + "..." if len(lead.email) > 30 else lead.email,
                lead.phone,
                lead.industry,
                f"{lead.confidence_score:.0f}%",
                "✅" if lead.linkedin else "❌"
            ])
        
        df = pd.DataFrame(table_data, columns=[
            'Company', 'Domain', 'Email', 'Phone', 'Industry', 'Score', 'LinkedIn'
        ])
        
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📋 Lead Details")
        
        for i, lead in enumerate(leads, 1):
            with st.expander(f"{i}. {lead.company_name} ({lead.confidence_score:.0f}% confidence)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**🌐 Domain:** {lead.domain}")
                    st.markdown(f"**📧 Email:** {lead.email or 'Not found'}")
                    st.markdown(f"**📞 Phone:** {lead.phone or 'Not found'}")
                    st.markdown(f"**🔗 LinkedIn:** {'Available' if lead.linkedin else 'Not found'}")
                
                with col2:
                    st.markdown(f"**🏢 Industry:** {lead.industry or 'Unknown'}")
                    st.markdown(f"**📍 Location:** {lead.location or 'N/A'}")
                    st.markdown(f"**💻 Tech Stack:** {lead.technology_stack or 'N/A'}")
                    st.markdown(f"**📊 Confidence:** {lead.confidence_score:.1f}%")
                
                if lead.description:
                    st.markdown(f"**📝 Description:** {lead.description[:150]}...")
    
    def _analytics_tab(self):
        st.header("📊 Lead Analytics")
        
        if 'leads' not in st.session_state or not st.session_state['leads']:
            st.info("No leads data available. Please generate leads first.")
            return
        
        leads = st.session_state['leads']
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Leads", len(leads))
        
        with col2:
            with_email = sum(1 for lead in leads if lead.email)
            email_pct = (with_email/len(leads)*100) if leads else 0
            st.metric("With Email", with_email, f"{email_pct:.1f}%")
        
        with col3:
            with_phone = sum(1 for lead in leads if lead.phone)
            phone_pct = (with_phone/len(leads)*100) if leads else 0
            st.metric("With Phone", with_phone, f"{phone_pct:.1f}%")
        
        with col4:
            avg_confidence = sum(lead.confidence_score for lead in leads) / len(leads)
            st.metric("Avg Confidence", f"{avg_confidence:.1f}%")

        if 'extraction_stats' in st.session_state:
            stats = st.session_state['extraction_stats']
            st.subheader("🔧 Extraction Method Performance")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Playwright", stats.get('playwright', 0))
            with col2:
                st.metric("BeautifulSoup", stats.get('beautifulsoup', 0))
            with col3:
                st.metric("Errors", stats.get('errors', 0))

        col1, col2 = st.columns(2)
        with col1:
            industry_counts = {}
            for lead in leads:
                industry = lead.industry or 'Unknown'
                industry_counts[industry] = industry_counts.get(industry, 0) + 1
            
            if industry_counts:
                fig = px.pie(
                    values=list(industry_counts.values()),
                    names=list(industry_counts.keys()),
                    title="Leads by Industry"
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            confidence_scores = [lead.confidence_score for lead in leads]
            fig = px.histogram(
                x=confidence_scores,
                nbins=10,
                title="Confidence Score Distribution",
                labels={'x': 'Confidence Score', 'y': 'Number of Leads'}
            )
            st.plotly_chart(fig, use_container_width=True)

        if any(lead.technology_stack for lead in leads):
            st.subheader("💻 Technology Stack Analysis")
            tech_counts = {}
            for lead in leads:
                if lead.technology_stack:
                    techs = [t.strip() for t in lead.technology_stack.split(',') if t.strip()]
                    for tech in techs:
                        tech_counts[tech] = tech_counts.get(tech, 0) + 1
            
            if tech_counts:
                tech_df = pd.DataFrame(list(tech_counts.items()), columns=['Technology', 'Count'])
                tech_df = tech_df.sort_values('Count', ascending=False).head(10)
                
                fig = px.bar(tech_df, x='Technology', y='Count', title="Top Technologies Detected")
                st.plotly_chart(fig, use_container_width=True)
    
    def _saved_leads_tab(self):
        st.header("📁 Saved Leads")
        if 'saved_leads' not in st.session_state:
            st.session_state['saved_leads'] = []

        if 'leads' in st.session_state and st.session_state['leads']:
            if st.button("💾 Save Current Leads"):
                st.session_state['saved_leads'].extend(st.session_state['leads'])
                st.success(f"Saved {len(st.session_state['leads'])} leads!")

        if st.session_state['saved_leads']:
            st.subheader(f"📋 {len(st.session_state['saved_leads'])} Saved Leads")

            df_data = []
            for i, lead in enumerate(st.session_state['saved_leads']):
                df_data.append({
                    'ID': i + 1,
                    'Company': lead.company_name,
                    'Domain': lead.domain,
                    'Email': lead.email,
                    'Phone': lead.phone,
                    'Industry': lead.industry,
                    'Confidence': f"{lead.confidence_score:.1f}%"
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            if st.button("🗑️ Clear Saved Leads"):
                st.session_state['saved_leads'] = []
                st.success("Cleared all saved leads!")
        else:
            st.info("No saved leads yet. Generate and save some leads first!")
    
    def _export_tab(self):
        st.header("📋 Export Leads")
        
        leads_to_export = []
        export_option = st.selectbox(
            "What to export:",
            ["Current Leads", "Saved Leads", "Both"]
        )
        
        if export_option == "Current Leads" and 'leads' in st.session_state:
            leads_to_export = st.session_state['leads']
        elif export_option == "Saved Leads" and 'saved_leads' in st.session_state:
            leads_to_export = st.session_state['saved_leads']
        elif export_option == "Both":
            current = st.session_state.get('leads', [])
            saved = st.session_state.get('saved_leads', [])
            leads_to_export = current + saved
        
        if not leads_to_export:
            st.info("No leads to export. Please generate some leads first.")
            return

        export_format = st.selectbox(
            "Export format:",
            ["CSV", "JSON", "Excel Compatible"]
        )

        export_data = []
        for lead in leads_to_export:
            export_data.append({
                'Company Name': lead.company_name,
                'Domain': lead.domain,
                'Email': lead.email if lead.email else '', 
                'Phone': lead.phone if lead.phone else '',
                'LinkedIn URL': lead.linkedin if lead.linkedin else '',
                'Industry': lead.industry if lead.industry else '',
                'Location': lead.location if lead.location else '',
                'Technology Stack': lead.technology_stack if lead.technology_stack else '',
                'Description': lead.description if lead.description else '',
                'Confidence Score': f"{lead.confidence_score:.1f}",
                'Has Email': 'Yes' if lead.email else 'No',
                'Has Phone': 'Yes' if lead.phone else 'No',
                'Has LinkedIn': 'Yes' if lead.linkedin else 'No'
            })
        
        df_export = pd.DataFrame(export_data)

        st.subheader("📊 Export Preview")

        preview_cols = ['Company Name', 'Domain', 'Email', 'Phone', 'Industry', 'Confidence Score']
        preview_df = df_export[preview_cols].head(10)
        st.dataframe(preview_df, use_container_width=True)

        with st.expander("📋 Complete Export Data Preview"):
            st.dataframe(df_export.head(5), use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            with_email = len([lead for lead in leads_to_export if lead.email])
            st.metric("Leads with Email", f"{with_email}/{len(leads_to_export)}")
        with col2:
            with_phone = len([lead for lead in leads_to_export if lead.phone]) 
            st.metric("Leads with Phone", f"{with_phone}/{len(leads_to_export)}")
        with col3:
            with_linkedin = len([lead for lead in leads_to_export if lead.linkedin])
            st.metric("Leads with LinkedIn", f"{with_linkedin}/{len(leads_to_export)}")

        st.subheader("💾 Download")
        
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        
        if export_format == "CSV":
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"leads_export_{timestamp}.csv",
                mime="text/csv"
            )

            st.code(csv.split('\\n')[0])
            if len(csv.split('\\n')) > 1:
                st.code(csv.split('\\n')[1])
        
        elif export_format == "JSON":
            json_data = df_export.to_json(orient='records', indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_data,
                file_name=f"leads_export_{timestamp}.json",
                mime="application/json"
            )
        
        elif export_format == "Excel Compatible":
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV (Excel Compatible)",
                data=csv,
                file_name=f"leads_export_{timestamp}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    app = LeadGeneratorApp()
    app.run()