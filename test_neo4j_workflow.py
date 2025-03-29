import unittest
import os
import logging
import json
import uuid
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set Neo4j environment variables if not already set
if not os.environ.get("NEO4J_URI"):
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
if not os.environ.get("NEO4J_USERNAME"):
    os.environ["NEO4J_USERNAME"] = "neo4j"
if not os.environ.get("NEO4J_PASSWORD"):
    os.environ["NEO4J_PASSWORD"] = "password"  # Replace with your actual password

# Import after environment variables are set
from LUNA.core.database import get_neo4j_driver
from LUNA.core.graph_engine import GraphWorkflowEngine
from LUNA.core.session_manager import get_session_manager
from LUNA.core.utility_registry import get_utility_registry
from LUNA.utils.request import request
from LUNA.utils.generate import generate
from LUNA.utils.reply import reply

class TestNeo4jWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Check Neo4j connection
        driver = get_neo4j_driver()
        try:
            with driver.get_session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()["count"]
                logger.info(f"Connected to Neo4j. Database has {count} nodes.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

        # Register utility functions
        registry = get_utility_registry()
        registry.register_utility("utils.request.request", request)
        registry.register_utility("utils.generate.generate", generate)
        registry.register_utility("utils.reply.reply", reply)

        # Load the conversation workflow
        cls.load_conversation_workflow()
        
    @classmethod
    def load_conversation_workflow(cls):
        """Load the conversation workflow from conversation_loop.cypher"""
        driver = get_neo4j_driver()
        try:
            # Read the Cypher file
            with open("conversation_loop.cypher", "r") as f:
                cypher = f.read()
                
            # Execute the Cypher script
            with driver.get_session() as session:
                # Delete any existing workflow nodes first
                session.run("MATCH (n:STEP) DETACH DELETE n")
                
                # Create new workflow
                session.run(cypher)
                
                # Verify that the workflow was created correctly
                result = session.run("MATCH (n:STEP) RETURN n.id as id")
                step_ids = [record["id"] for record in result]
                logger.info(f"Created workflow with steps: {step_ids}")
                
                # Verify relationships
                result = session.run("""
                    MATCH (s:STEP)-[r:NEXT]->(t:STEP)
                    RETURN s.id as source, t.id as target
                """)
                relationships = [(record["source"], record["target"]) for record in result]
                logger.info(f"Created relationships: {relationships}")
        except Exception as e:
            logger.error(f"Failed to load workflow: {e}")
            raise

    def setUp(self):
        """Set up test environment for each test"""
        self.session_manager = get_session_manager()
        self.engine = GraphWorkflowEngine(session_manager=self.session_manager)
        self.session_id = str(uuid.uuid4())
        logger.info(f"Creating test session: {self.session_id}")
        self.session_manager.create_session(self.session_id)
        
    def test_01_initial_greeting(self):
        """Test that the workflow correctly processes the root and request steps"""
        # Process workflow initially
        status = self.engine.process_workflow(self.session_id)
        logger.info(f"Initial workflow status: {status}")
        
        # Verify that workflow is in awaiting_input state
        self.assertEqual(status, "awaiting_input", 
                         "Workflow should be awaiting input after initialization")
        
        # Get current state
        state = self.session_manager.get_session_state(self.session_id)
        
        # Verify root step is complete
        self.assertIn("root", state["workflow"], "Root step should exist in workflow")
        self.assertEqual(state["workflow"]["root"]["status"], "complete", 
                         "Root step should be marked as complete")
        
        # Verify request step is awaiting input
        self.assertIn("request", state["workflow"], "Request step should exist in workflow")
        self.assertEqual(state["workflow"]["request"]["status"], "awaiting_input", 
                         "Request step should be awaiting input")
        
        # Check that request step has the correct prompt
        outputs = state["data"]["outputs"]
        self.assertIn("request", outputs, "Request step should have outputs")
        self.assertIn("prompt", outputs["request"], "Request output should include prompt")
        self.assertEqual(outputs["request"]["prompt"], "GM! How can I help?",
                         "Initial prompt should be the default greeting")

    def test_02_full_conversation_loop(self):
        """Test a complete conversation loop with input, response, and followup"""
        # Start workflow
        self.engine.process_workflow(self.session_id)
        
        # Get initial state
        initial_state = self.session_manager.get_session_state(self.session_id)
        logger.info(f"Initial workflow statuses: {[(s, initial_state['workflow'][s]['status']) for s in initial_state['workflow']]}")
        
        # Send first user message
        test_message = "Tell me about Neo4j graph databases"
        logger.info(f"Sending user message: {test_message}")
        status = self.engine.handle_user_input(self.session_id, test_message)
        self.assertEqual(status, "active", "Workflow should be active after receiving input")
        
        # Process workflow after first message
        process_status = self.engine.process_workflow(self.session_id)
        logger.info(f"Status after processing: {process_status}")
        
        # Get updated state
        state = self.session_manager.get_session_state(self.session_id)
        logger.info(f"Workflow statuses: {[(s, state['workflow'][s]['status']) for s in state['workflow']]}")
        
        # Verify all steps processed correctly
        self.assertEqual(state["workflow"]["request"]["status"], "complete", "Request step should be complete")
        self.assertEqual(state["workflow"]["generate"]["status"], "complete", "Generate step should be complete")
        self.assertEqual(state["workflow"]["reply"]["status"], "complete", "Reply step should be complete")
        
        # Check that generate step produced the required fields
        generate_output = state["data"]["outputs"]["generate"]
        self.assertIn("response", generate_output, "Generate should include response")
        self.assertIn("followup", generate_output, "Generate should include followup")
        self.assertIn("merits_followup", generate_output, "Generate should include merits_followup flag")
        
        # Check that reply step used the response from generate
        self.assertEqual(state["data"]["outputs"]["reply"]["message"], 
                         generate_output["response"],
                         "Reply message should match generated response")
        
        # Check if we looped back to request
        if process_status == "awaiting_input" and generate_output["merits_followup"]:
            # We looped back - check if the prompt was updated
            self.assertIn("request", state["data"]["outputs"])
            self.assertIn("prompt", state["data"]["outputs"]["request"])
            updated_prompt = state["data"]["outputs"]["request"]["prompt"]
            logger.info(f"Updated prompt for second round: {updated_prompt}")
            
            # Verify it's the followup question
            self.assertEqual(updated_prompt, generate_output["followup"],
                             "Second prompt should be the followup question")
            
            # Send a second message to complete the loop
            second_message = "Yes, tell me more about Neo4j's Cypher query language"
            logger.info(f"Sending second message: {second_message}")
            status = self.engine.handle_user_input(self.session_id, second_message)
            self.assertEqual(status, "active", "Workflow should be active after second message")
            
            # Process workflow after second message
            second_status = self.engine.process_workflow(self.session_id)
            logger.info(f"Status after second processing: {second_status}")
            
            # Get final state
            final_state = self.session_manager.get_session_state(self.session_id)
            logger.info(f"Final workflow statuses: {[(s, final_state['workflow'][s]['status']) for s in final_state['workflow']]}")
            
            # Verify second response was generated correctly
            self.assertEqual(final_state["workflow"]["generate"]["status"], "complete", 
                             "Generate step should be complete in second round")
            self.assertEqual(final_state["workflow"]["reply"]["status"], "complete", 
                             "Reply step should be complete in second round")
            
            second_generate = final_state["data"]["outputs"]["generate"]
            self.assertIn("response", second_generate, "Second generate should include response")
            
    def tearDown(self):
        """Clean up after each test"""
        logger.info(f"Test complete for session: {self.session_id}")
        # Optionally delete the session
        # self.session_manager.delete_session(self.session_id)

if __name__ == "__main__":
    unittest.main() 