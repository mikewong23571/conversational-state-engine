"""
End-to-end test for login story flow
"""
import pytest
import json
import requests
from typing import Dict, Any

# 测试服务器地址
BASE_URL = "http://localhost:8000/api"

class TestLoginStoryFlow:
    """测试登录故事的完整流程"""
    
    @pytest.fixture
    def session_id(self):
        """创建测试会话"""
        response = requests.post(f"{BASE_URL}/sessions")
        assert response.status_code == 200
        data = response.json()
        return data["session_id"]
    
    def test_complete_flow(self, session_id):
        """完整的端到端测试流程"""
        
        # Step 1: 获取初始状态
        response = requests.get(f"{BASE_URL}/sessions/{session_id}/state")
        assert response.status_code == 200
        initial_state = response.json()
        assert initial_state["version"] == "v1"
        assert len(initial_state["data"]["stories"]) == 0
        
        # Step 2: 提交意图 - 添加登录故事
        intentions = {
            "items": [
                {
                    "action": "add",
                    "target_path": "/stories/-",
                    "value": {
                        "key": "AUTH-Login",
                        "title": "登录（移动+生物识别）",
                        "priority": "P0",
                        "platform": ["iOS", "Android"],
                        "acceptance_criteria": [
                            "支持生物识别",
                            "失败三次锁定5分钟"
                        ],
                        "dependencies": ["AUTH-SSO"],
                        "auth_type": "local"
                    },
                    "reason": "用户请求：新增登录故事，移动端优先",
                    "confidence": 0.8
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/intents",
            json=intentions
        )
        assert response.status_code == 200
        intent_result = response.json()
        intention_set_id = intent_result["intention_set_id"]
        
        # Step 3: 生成补丁提案
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/patch-proposals",
            json={"intention_set_id": intention_set_id}
        )
        assert response.status_code == 200
        proposal = response.json()
        proposal_id = proposal["proposal_id"]
        
        # 验证影响分析
        assert "impact_analysis" in proposal
        impact = proposal["impact_analysis"]
        assert "risk_level" in impact
        assert "semantic_conflicts" in impact
        
        # 检查是否检测到认证方法冲突
        conflicts = impact["semantic_conflicts"]
        auth_conflicts = [c for c in conflicts if c["rule"] == "auth_method_conflict"]
        if auth_conflicts:
            print(f"检测到认证冲突: {auth_conflicts[0]['message']}")
        
        # Step 4: 渐进式确认 - 意图确认
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/confirm",
            params={"stage": "intent"},
            json={"proposal_id": proposal_id}
        )
        assert response.status_code == 200
        
        # Step 5: 渐进式确认 - 变更确认
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/confirm",
            params={"stage": "change"},
            json={
                "proposal_id": proposal_id,
                "accept_patch_indices": [0],  # 接受所有补丁
                "apply_auto_fixes": False
            }
        )
        assert response.status_code == 200
        
        # Step 6: 渐进式确认 - 副作用确认
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/confirm",
            params={"stage": "side_effect"},
            json={
                "proposal_id": proposal_id,
                "apply_auto_fixes": True  # 应用自动修复
            }
        )
        assert response.status_code == 200
        
        # Step 7: 提交变更
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/commit",
            json={
                "proposal_id": proposal_id,
                "message": "添加移动端登录功能"
            }
        )
        assert response.status_code == 200
        commit_result = response.json()
        
        # 验证提交结果
        assert "commit_id" in commit_result
        assert "version" in commit_result
        assert commit_result["version"] == "v2"
        assert "artifacts" in commit_result
        
        # Step 8: 验证新状态
        response = requests.get(f"{BASE_URL}/sessions/{session_id}/state")
        assert response.status_code == 200
        new_state = response.json()
        
        assert new_state["version"] == "v2"
        assert len(new_state["data"]["stories"]) == 1
        
        story = new_state["data"]["stories"][0]
        assert story["key"] == "AUTH-Login"
        assert story["priority"] == "P0"
        assert "iOS" in story["platform"]
        assert "Android" in story["platform"]
        
        # Step 9: 获取生成的artifacts
        response = requests.get(
            f"{BASE_URL}/sessions/{session_id}/artifacts",
            params={"version": "v2"}
        )
        assert response.status_code == 200
        artifacts = response.json()
        
        assert len(artifacts["items"]) >= 2  # 至少有markdown和csv
        
        # 找到markdown artifact
        markdown_artifacts = [a for a in artifacts["items"] if a["type"] == "markdown"]
        assert len(markdown_artifacts) > 0
        
        print(f"测试通过！新版本: v2, 包含 {len(artifacts['items'])} 个artifacts")
    
    def test_conflict_detection(self, session_id):
        """测试冲突检测功能"""
        
        # 先添加一个SSO故事
        intentions_sso = {
            "items": [
                {
                    "action": "add",
                    "target_path": "/stories/-",
                    "value": {
                        "key": "AUTH-SSO",
                        "title": "单点登录",
                        "priority": "P1",
                        "auth_type": "SSO",
                        "acceptance_criteria": ["支持企业IdP"]
                    }
                }
            ]
        }
        
        # 创建并提交SSO故事
        response = requests.post(f"{BASE_URL}/sessions/{session_id}/intents", json=intentions_sso)
        intent_id = response.json()["intention_set_id"]
        
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/patch-proposals",
            json={"intention_set_id": intent_id}
        )
        proposal_id = response.json()["proposal_id"]
        
        # 快速提交
        for stage in ["intent", "change", "side_effect"]:
            requests.post(
                f"{BASE_URL}/sessions/{session_id}/confirm",
                params={"stage": stage},
                json={"proposal_id": proposal_id}
            )
        
        requests.post(
            f"{BASE_URL}/sessions/{session_id}/commit",
            json={"proposal_id": proposal_id}
        )
        
        # 现在尝试添加有冲突的故事
        intentions_conflict = {
            "items": [
                {
                    "action": "add",
                    "target_path": "/stories/-",
                    "value": {
                        "key": "AUTH-Login",
                        "title": "登录功能",
                        "priority": "P0",
                        "auth_type": "SSO",
                        "acceptance_criteria": [
                            "支持SSO登录",
                            "需要local_password作为备用"  # 这会触发冲突
                        ],
                        "dependencies": ["AUTH-SSO"]
                    }
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/sessions/{session_id}/intents", json=intentions_conflict)
        intent_id = response.json()["intention_set_id"]
        
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/patch-proposals",
            json={"intention_set_id": intent_id}
        )
        proposal = response.json()
        
        # 验证冲突检测
        conflicts = proposal["impact_analysis"]["semantic_conflicts"]
        auth_conflicts = [c for c in conflicts if c["rule"] == "auth_method_conflict"]
        
        assert len(auth_conflicts) > 0, "应该检测到认证方法冲突"
        assert auth_conflicts[0]["severity"] == "high"
        print(f"成功检测到冲突: {auth_conflicts[0]['message']}")
    
    def test_dependency_order_check(self, session_id):
        """测试依赖优先级检查"""
        
        intentions = {
            "items": [
                {
                    "action": "add",
                    "target_path": "/stories/-",
                    "value": {
                        "key": "FEATURE-A",
                        "title": "功能A",
                        "priority": "P0",
                        "dependencies": ["FEATURE-B"]
                    }
                },
                {
                    "action": "add",
                    "target_path": "/stories/-",
                    "value": {
                        "key": "FEATURE-B",
                        "title": "功能B",
                        "priority": "P2"  # 优先级低于A，应该触发警告
                    }
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/sessions/{session_id}/intents", json=intentions)
        intent_id = response.json()["intention_set_id"]
        
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/patch-proposals",
            json={"intention_set_id": intent_id}
        )
        proposal = response.json()
        
        # 检查依赖优先级冲突
        conflicts = proposal["impact_analysis"]["semantic_conflicts"]
        dep_conflicts = [c for c in conflicts if c["rule"] == "dependency_order"]
        
        assert len(dep_conflicts) > 0, "应该检测到依赖优先级问题"
        print(f"检测到依赖问题: {dep_conflicts[0]['message']}")

if __name__ == "__main__":
    # 运行测试
    import sys
    
    # 创建测试实例
    test = TestLoginStoryFlow()
    
    # 创建会话
    response = requests.post(f"{BASE_URL}/sessions")
    if response.status_code != 200:
        print("无法连接到服务器，请确保服务器正在运行")
        sys.exit(1)
    
    session_id = response.json()["session_id"]
    print(f"创建测试会话: {session_id}")
    
    # 运行测试
    try:
        print("\n运行完整流程测试...")
        test.test_complete_flow(session_id)
        print("✓ 完整流程测试通过")
        
        # 创建新会话进行冲突测试
        response = requests.post(f"{BASE_URL}/sessions")
        session_id2 = response.json()["session_id"]
        
        print("\n运行冲突检测测试...")
        test.test_conflict_detection(session_id2)
        print("✓ 冲突检测测试通过")
        
        # 创建新会话进行依赖测试
        response = requests.post(f"{BASE_URL}/sessions")
        session_id3 = response.json()["session_id"]
        
        print("\n运行依赖检查测试...")
        test.test_dependency_order_check(session_id3)
        print("✓ 依赖检查测试通过")
        
        print("\n所有测试通过！✨")
        
    except AssertionError as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)
