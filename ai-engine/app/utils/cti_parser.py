import json
import logging
from typing import Dict, List, Any
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

class CTIParser:
    def __init__(self):
        self.sources = {
            'cisa': 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json',
            'mitre': 'https://cve.circl.lu/api/last',
            'threatfox': 'https://threatfox-api.abuse.ch/api/v1/'
        }
        
    async def fetch_cti_data(self, source: str) -> List[Dict]:
        """Fetch CTI data from specified source"""
        try:
            if source not in self.sources:
                raise ValueError(f"Unknown CTI source: {source}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.sources[source], timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.parse_source_data(source, data)
                    else:
                        logger.warning(f"Failed to fetch from {source}: HTTP {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching from {source}: {e}")
            return []
    
    def parse_source_data(self, source: str, data: Any) -> List[Dict]:
        """Parse data based on source format"""
        if source == 'cisa':
            return self.parse_cisa_data(data)
        elif source == 'mitre':
            return self.parse_mitre_data(data)
        elif source == 'threatfox':
            return self.parse_threatfox_data(data)
        else:
            return []
    
    def parse_cisa_data(self, data: Dict) -> List[Dict]:
        """Parse CISA known exploited vulnerabilities"""
        threats = []
        if 'vulnerabilities' in data:
            for vuln in data['vulnerabilities']:
                threat = {
                    'source': 'cisa',
                    'cve_id': vuln.get('cveID', ''),
                    'title': vuln.get('vulnerabilityName', ''),
                    'description': vuln.get('shortDescription', ''),
                    'severity': self.map_cisa_severity(vuln.get('knownRansomwareCampaignUse', '')),
                    'published_date': vuln.get('dateAdded', ''),
                    'references': vuln.get('references', []),
                    'type': 'vulnerability'
                }
                threats.append(threat)
        return threats
    
    def parse_mitre_data(self, data: List[Dict]) -> List[Dict]:
        """Parse MITRE CVE data"""
        threats = []
        for cve in data:
            threat = {
                'source': 'mitre',
                'cve_id': cve.get('id', ''),
                'title': f"CVE-{cve.get('id', '')}",
                'description': cve.get('summary', ''),
                'severity': self.map_cvss_severity(cve.get('cvss', 0)),
                'published_date': cve.get('Published', ''),
                'references': cve.get('references', []),
                'type': 'vulnerability'
            }
            threats.append(threat)
        return threats
    
    def parse_threatfox_data(self, data: Dict) -> List[Dict]:
        """Parse ThreatFox IOC data"""
        threats = []
        if data.get('query_status') == 'ok' and 'data' in data:
            for ioc in data['data']:
                threat = {
                    'source': 'threatfox',
                    'ioc': ioc.get('ioc', ''),
                    'title': ioc.get('threat_type', ''),
                    'description': ioc.get('malware', ''),
                    'severity': 'HIGH',  # ThreatFox IOCs are typically high severity
                    'published_date': ioc.get('first_seen', ''),
                    'references': [],
                    'type': 'ioc'
                }
                threats.append(threat)
        return threats
    
    def map_cisa_severity(self, ransomware_use: str) -> str:
        """Map CISA ransomware use to severity"""
        if ransomware_use.lower() == 'known':
            return 'CRITICAL'
        return 'HIGH'
    
    def map_cvss_severity(self, cvss_score: float) -> str:
        """Map CVSS score to severity"""
        if cvss_score >= 9.0:
            return 'CRITICAL'
        elif cvss_score >= 7.0:
            return 'HIGH'
        elif cvss_score >= 4.0:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    async def get_all_threats(self) -> List[Dict]:
        """Get threats from all sources"""
        all_threats = []
        
        for source in self.sources:
            threats = await self.fetch_cti_data(source)
            all_threats.extend(threats)
        
        # Deduplicate and sort by severity
        unique_threats = self.deduplicate_threats(all_threats)
        return sorted(unique_threats, key=lambda x: self.severity_weight(x['severity']), reverse=True)
    
    def deduplicate_threats(self, threats: List[Dict]) -> List[Dict]:
        """Remove duplicate threats based on CVE ID or IOC"""
        seen = set()
        unique_threats = []
        
        for threat in threats:
            identifier = threat.get('cve_id') or threat.get('ioc') or threat['title']
            if identifier not in seen:
                seen.add(identifier)
                unique_threats.append(threat)
        
        return unique_threats
    
    def severity_weight(self, severity: str) -> int:
        """Convert severity to weight for sorting"""
        weights = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        return weights.get(severity.upper(), 0)