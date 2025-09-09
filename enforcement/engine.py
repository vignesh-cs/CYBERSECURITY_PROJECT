import asyncio
import logging
import json
import aiohttp
import asyncpg
from typing import Dict, List, Any
import subprocess
import tempfile
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnforcementEngine:
    def __init__(self):
        self.db_pool = None
        self.session = None
        self.ansible_path = "/ansible"
        
    async def initialize(self):
        """Initialize database connection and HTTP session"""
        try:
            self.db_pool = await asyncpg.create_pool(
                os.getenv('DATABASE_URL', 'postgresql://admin:securepassword123@postgres:5432/compliance_db')
            )
            self.session = aiohttp.ClientSession()
            logger.info("Enforcement Engine initialized successfully")
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    async def process_pending_actions(self):
        """Process pending compliance actions from database"""
        while True:
            try:
                async with self.db_pool.acquire() as conn:
                    # Get pending actions
                    actions = await conn.fetch('''
                        SELECT * FROM compliance_actions 
                        WHERE status = 'PENDING' 
                        ORDER BY created_at ASC
                        LIMIT 10
                    ''')
                    
                    for action in actions:
                        await self.execute_action(dict(action))
                        
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error processing actions: {e}")
                await asyncio.sleep(30)

    async def execute_action(self, action: Dict[str, Any]):
        """Execute a compliance action using Ansible"""
        try:
            action_type = action['action_taken']
            target_endpoints = action.get('target_endpoints', [])
            
            logger.info(f"Executing action {action_type} on endpoints: {target_endpoints}")
            
            # Map action to Ansible playbook
            playbook_mapping = {
                'DISABLE_SMBv1': 'disable_smbv1.yml',
                'UPDATE_FIREWALL': 'update_firewall.yml',
                'ISOLATE_ENDPOINT': 'isolate_endpoint.yml',
                'BLOCK_RDP_PORT': 'update_firewall.yml',
                'ENABLE_FIREWALL': 'update_firewall.yml'
            }
            
            playbook = playbook_mapping.get(action_type)
            if not playbook:
                logger.warning(f"No playbook mapping for action: {action_type}")
                return

            # Create inventory file for target endpoints
            inventory_content = self.create_inventory(target_endpoints)
            
            # Execute Ansible playbook
            result = await self.run_ansible_playbook(playbook, inventory_content, action)
            
            # Update action status
            await self.update_action_status(action['id'], 'EXECUTED' if result else 'FAILED')
            
            logger.info(f"Action {action_type} executed successfully: {result}")
            
        except Exception as e:
            logger.error(f"Failed to execute action {action['id']}: {e}")
            await self.update_action_status(action['id'], 'FAILED')

    def create_inventory(self, endpoints: List[Dict]) -> str:
        """Create Ansible inventory from endpoints"""
        inventory = {
            'all': {
                'children': {
                    'windows_servers': {'hosts': {}},
                    'linux_servers': {'hosts': {}},
                    'workstations': {'hosts': {}}
                }
            }
        }
        
        for endpoint in endpoints:
            host_data = {
                'ansible_host': endpoint.get('ip_address', endpoint['hostname']),
                'ansible_user': 'administrator' if 'windows' in endpoint.get('os_type', '').lower() else 'ubuntu'
            }
            
            if 'server' in endpoint['hostname']:
                if 'windows' in endpoint.get('os_type', '').lower():
                    inventory['all']['children']['windows_servers']['hosts'][endpoint['hostname']] = host_data
                else:
                    inventory['all']['children']['linux_servers']['hosts'][endpoint['hostname']] = host_data
            else:
                inventory['all']['children']['workstations']['hosts'][endpoint['hostname']] = host_data
        
        return json.dumps(inventory, indent=2)

    async def run_ansible_playbook(self, playbook: str, inventory: str, action: Dict) -> bool:
        """Execute Ansible playbook"""
        try:
            # Create temporary inventory file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as inv_file:
                inv_file.write(inventory)
                inv_file_path = inv_file.name
            
            # Create extra variables for Ansible
            extra_vars = {
                'action_id': action['id'],
                'threat_description': action.get('threat_description', ''),
                'target_hosts': list(json.loads(inventory)['all']['children'].keys())
            }
            
            # Build command
            cmd = [
                'ansible-playbook',
                '-i', inv_file_path,
                f'{self.ansible_path}/playbooks/{playbook}',
                '--extra-vars', json.dumps(extra_vars),
                '-v'
            ]
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Clean up
            os.unlink(inv_file_path)
            
            if process.returncode == 0:
                logger.info(f"Playbook {playbook} executed successfully")
                logger.debug(f"Ansible output: {stdout.decode()}")
                return True
            else:
                logger.error(f"Playbook {playbook} failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error running Ansible playbook: {e}")
            return False

    async def update_action_status(self, action_id: str, status: str):
        """Update action status in database"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    UPDATE compliance_actions 
                    SET status = $1, executed_at = $2
                    WHERE id = $3
                ''', status, datetime.utcnow(), action_id)
        except Exception as e:
            logger.error(f"Failed to update action status: {e}")

    async def monitor_endpoints(self):
        """Monitor endpoint status and health"""
        while True:
            try:
                async with self.db_pool.acquire() as conn:
                    endpoints = await conn.fetch('SELECT * FROM endpoints WHERE status = $1', 'ONLINE')
                    
                    for endpoint in endpoints:
                        is_online = await self.check_endpoint_health(dict(endpoint))
                        if not is_online:
                            await conn.execute(
                                'UPDATE endpoints SET status = $1 WHERE id = $2',
                                'OFFLINE', endpoint['id']
                            )
                            logger.warning(f"Endpoint {endpoint['hostname']} is offline")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Endpoint monitoring error: {e}")
                await asyncio.sleep(300)

    async def check_endpoint_health(self, endpoint: Dict) -> bool:
        """Check if endpoint is responsive"""
        try:
            if 'windows' in endpoint.get('os_type', '').lower():
                # Check Windows endpoint
                cmd = ['ping', '-n', '1', '-w', '1000', endpoint['ip_address']]
            else:
                # Check Linux endpoint
                cmd = ['ping', '-c', '1', '-W', '1', endpoint['ip_address']]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception:
            return False

    async def run(self):
        """Main execution loop"""
        await self.initialize()
        
        # Start all monitoring tasks
        tasks = [
            self.process_pending_actions(),
            self.monitor_endpoints()
        ]
        
        await asyncio.gather(*tasks)

async def main():
    engine = EnforcementEngine()
    await engine.run()

if __name__ == '__main__':
    asyncio.run(main())