"""
TikAPI テストスクリプト
TikAPIの精度・速度・安定性を検証
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

class TikAPITester:
    """TikAPI テストクラス"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tikapi.io/public/v1"
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
    def check_user_live_status(self, username: str) -> Dict:
        """
        ユーザーのライブ配信状態をチェック
        
        Args:
            username: TikTokユーザー名（@なし）
            
        Returns:
            結果辞書
        """
        start_time = time.time()
        
        try:
            # TikAPIでユーザー情報取得
            url = f"{self.base_url}/user/info"
            params = {"username": username}
            
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params,
                timeout=15
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # ライブ状態を判定
                # 注: TikAPIのレスポンス構造に応じて調整が必要
                is_live = self._extract_live_status(data)
                
                return {
                    "username": username,
                    "success": True,
                    "is_live": is_live,
                    "response_time": elapsed_time,
                    "timestamp": datetime.now().isoformat(),
                    "status_code": response.status_code,
                    "raw_data": data
                }
            else:
                return {
                    "username": username,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_time": elapsed_time,
                    "timestamp": datetime.now().isoformat()
                }
                
        except requests.exceptions.Timeout:
            return {
                "username": username,
                "success": False,
                "error": "Timeout",
                "response_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "username": username,
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_live_status(self, data: Dict) -> bool:
        """
        APIレスポンスからライブ状態を抽出
        
        注: TikAPIの実際のレスポンス構造に応じて調整が必要
        """
        try:
            # 例: data['user']['is_live'] のような構造を想定
            # 実際のレスポンスを確認して調整してください
            if 'user' in data:
                return data['user'].get('is_live', False)
            elif 'data' in data:
                return data['data'].get('is_live', False)
            return False
        except:
            return False
    
    def test_multiple_users(self, usernames: List[str], iterations: int = 1) -> Dict:
        """
        複数ユーザーをテスト
        
        Args:
            usernames: ユーザー名リスト
            iterations: 繰り返し回数
            
        Returns:
            テスト結果
        """
        results = []
        
        for i in range(iterations):
            print(f"\n{'='*50}")
            print(f"反復 {i+1}/{iterations}")
            print(f"{'='*50}\n")
            
            for username in usernames:
                print(f"テスト中: @{username}...", end=" ")
                result = self.check_user_live_status(username)
                results.append(result)
                
                status = "✅ 成功" if result["success"] else "❌ 失敗"
                live_status = "🔴 LIVE" if result.get("is_live") else "⚪ オフライン"
                time_ms = result["response_time"] * 1000
                
                print(f"{status} | {live_status} | {time_ms:.0f}ms")
                
                # レート制限対策（少し待機）
                time.sleep(1)
        
        return self._generate_summary(results)
    
    def _generate_summary(self, results: List[Dict]) -> Dict:
        """テスト結果のサマリーを生成"""
        total = len(results)
        successful = len([r for r in results if r["success"]])
        failed = total - successful
        
        response_times = [r["response_time"] for r in results if r["success"]]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        
        live_count = len([r for r in results if r.get("is_live")])
        
        summary = {
            "total_tests": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "average_response_time": avg_response,
            "live_detected": live_count,
            "offline_detected": successful - live_count,
            "results": results
        }
        
        return summary


def main():
    """メイン実行関数"""
    
    print("="*60)
    print("TikAPI テストシステム")
    print("="*60)
    print()
    
    # APIキー取得
    api_key = os.getenv("TIKAPI_KEY")
    if not api_key:
        print("❌ エラー: TIKAPI_KEYが設定されていません")
        print("   .envファイルにAPIキーを設定してください")
        return
    
    # テスト対象ユーザー
    test_users_str = os.getenv("TEST_USERS", "takehiko1026")
    test_users = [u.strip() for u in test_users_str.split(",")]
    
    print(f"📋 テスト対象ユーザー: {len(test_users)}名")
    for user in test_users:
        print(f"   - @{user}")
    print()
    
    # テスト実行
    tester = TikAPITester(api_key)
    
    # 1回のテスト実行
    print("🚀 テスト開始...")
    summary = tester.test_multiple_users(test_users, iterations=1)
    
    # 結果表示
    print("\n" + "="*60)
    print("📊 テスト結果サマリー")
    print("="*60)
    print(f"総テスト数: {summary['total_tests']}")
    print(f"成功: {summary['successful']}")
    print(f"失敗: {summary['failed']}")
    print(f"成功率: {summary['success_rate']:.1f}%")
    print(f"平均レスポンス時間: {summary['average_response_time']*1000:.0f}ms")
    print(f"ライブ検出: {summary['live_detected']}名")
    print(f"オフライン検出: {summary['offline_detected']}名")
    print()
    
    # 結果をJSONファイルに保存
    output_file = "test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 結果を {output_file} に保存しました")
    print()
    
    # 次のステップ提案
    print("="*60)
    print("📌 次のステップ")
    print("="*60)
    print("1. test_results.jsonで詳細を確認")
    print("2. 成功率が高ければ、より多くのユーザーでテスト")
    print("3. 現在のシステム（TikTokLive）と比較")
    print("4. レスポンス時間と精度を評価")
    print()


if __name__ == "__main__":
    main()
