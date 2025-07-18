#!/usr/bin/env python3
"""
Test script to run the ClouvelPromoterAgent locally and show results
"""
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from agents.clouvel_promoter_agent import ClouvelPromoterAgent

def test_promoter_agent():
    """Test the promoter agent with current configuration"""
    
    print("🚀 Testing ClouvelPromoterAgent Locally")
    print("=" * 50)
    
    try:
        # Initialize the agent in dry run mode
        agent = ClouvelPromoterAgent(dry_run=True)
        
        print("✅ Agent initialized successfully")
        
        # Get current status
        print("\n📊 Current Agent Status:")
        status = agent.get_status()
        
        if "error" in status:
            print(f"❌ Error getting status: {status['error']}")
            return
        
        # Print key metrics
        print(f"   • Current karma: {status.get('current_karma', 'Unknown')}")
        print(f"   • Karma target: {status.get('karma_target', 'Unknown')}")
        print(f"   • Karma building enabled: {status.get('karma_building_enabled', 'Unknown')}")
        print(f"   • Promotional probability: {status.get('promotional_probability', 'Unknown')}")
        print(f"   • Total scanned: {status.get('total_scanned', 0)}")
        print(f"   • Total promoted: {status.get('total_promoted', 0)}")
        print(f"   • Karma building engagements: {status.get('karma_building_engagements', 0)}")
        print(f"   • Unique karma subreddits: {status.get('unique_karma_subreddits', 0)}")
        print(f"   • Available karma subreddits: {status.get('karma_subreddits_available', 0)}")
        
        # Test karma building cycle
        print("\n🎨 Testing Karma Building Cycle:")
        karma_results = agent.run_karma_building_only()
        
        if karma_results:
            print(f"   • Attempted {len(karma_results)} karma building posts")
            successful = [r for r in karma_results if r.get('processed')]
            print(f"   • Successful engagements: {len(successful)}")
            
            for result in karma_results[:3]:  # Show first 3 results
                subreddit = result.get('subreddit', 'Unknown')
                action = result.get('action', 'Unknown')
                error = result.get('error', '')
                print(f"     - r/{subreddit}: {action} {f'(Error: {error})' if error else ''}")
        else:
            print("   • No karma building attempts (likely above karma target)")
        
        # Test main promotion cycle
        print("\n🏰 Testing Main Promotion Cycle:")
        main_result = agent.run_single_cycle()
        
        print(f"   • Processed: {main_result.get('processed', False)}")
        print(f"   • Action: {main_result.get('action', 'None')}")
        print(f"   • Post ID: {main_result.get('post_id', 'None')}")
        
        if main_result.get('error'):
            print(f"   • Error: {main_result['error']}")
        
        # Test comment pattern selection
        print("\n💬 Testing Comment Pattern Selection:")
        for i in range(3):
            pattern = agent._select_comment_pattern()
            print(f"   • Pattern {i+1}: {pattern['name']} ({pattern['link_placement']} placement, {pattern['length_target']} length)")
        
        # Test subreddit context
        print("\n🗺️ Testing Subreddit Context Recognition:")
        test_subreddits = ["art", "aww", "todayilearned", "AskReddit", "funny"]
        for sub in test_subreddits:
            context = agent._get_subreddit_context(sub)
            print(f"   • r/{sub}: {context[:60]}...")
        
        print("\n✅ All tests completed successfully!")
        print("\n🔧 Configuration Summary:")
        print(f"   • User Agent: {os.getenv('PROMOTER_AGENT_USER_AGENT', 'Not set')}")
        print(f"   • Dry Run: {agent.dry_run}")
        print(f"   • Promotional Probability: {agent.promotional_probability}")
        print(f"   • Karma Target: {agent.karma_target}")
        print(f"   • Available Karma Subreddits: {len(agent.karma_subreddits)}")
        
    except Exception as e:
        print(f"❌ Error testing agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_promoter_agent()