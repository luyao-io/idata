import time
import json
from typing import Dict, Any
from logger.log import SysLogger
from utils.kafka_manager import KafkaManager
from config.context import request_user
from datetime import datetime

class EventParser:
    def __init__(self):
        self.metrics = {
            "input": 0, 
            "output": 0, 
            "total_tokens": 0,
            "start_time": None,
            "first_token_time": None
        }
        self.kafka_manager = KafkaManager()

    def parse_event(self, event):
        try:
            event_type = event["event"]
            data = event.get("data", {})
            run_id = event.get("run_id")
            # SysLogger.info(event)

            # 记录模型开始调用的时间
            if event_type == "on_chat_model_start":
                if self.metrics["start_time"] is None:
                    self.metrics["start_time"] = time.perf_counter()

            # 捕获第一个数据片段并计算耗时
            if event_type == "on_chat_model_stream":
                if self.metrics["first_token_time"] is None and self.metrics["start_time"] is not None:
                    first_token_time = time.perf_counter()
                    ttft = first_token_time - self.metrics["start_time"]
                    self.metrics["first_token_time"] = ttft
                    
            # 添加token使用统计
            if event_type == "on_chat_model_end":
                # 获取token使用信息
                metadata = data.get("output")

                # 获取token使用信息
                usage = metadata.usage_metadata

                if usage:
                    # 累加每一轮调用的 token
                    self.metrics["input"] +=usage.get("input_tokens", 0)
                    self.metrics["output"] += usage.get("output_tokens", 0)
                    self.metrics["total_tokens"] +=usage.get("total_tokens", 0)


            if event_type == "on_chat_model_stream":
                ai_chunk = data.get("chunk")
                if ai_chunk and hasattr(ai_chunk, "content"):
                    content = ai_chunk.content
                    if content:
                        return {
                            "type": "text",
                            "payload":
                                {
                                    "content": content
                                }
                        }

            if event_type == "on_tool_start":
                tool_name = event.get("name", "")
                input_data = data.get("input", {})

                if tool_name == "load_skill" and input_data:
                    return {
                        "type": "skill",
                        "payload":
                            {
                                "action": "start",
                                "name": tool_name,
                                "run_id": run_id,
                                "input": input_data
                            }
                    }
                elif tool_name == "write_todos" and input_data:
                    return {
                        "type": "plan",
                        "payload":
                            {
                                "action": "start",
                                "name": tool_name,
                                "run_id": run_id,
                                "input": input_data
                            }
                    }

                else:
                    return {
                        "type": "tool",
                        "payload":
                            {
                                "action": "start",
                                "name": tool_name,
                                "run_id": run_id,
                                "input": input_data
                            }
                    }

            if event_type == "on_tool_end":
                tool_name = event.get("name", "")
                output_data = data.get("output", "")

                if tool_name == "load_skill":
                    # 安全地访问嵌套属性
                    output = data.get("output", {})
                    if isinstance(output, dict) and "update" in output:
                        update_data = output.get("update", {})
                        if isinstance(update_data, dict) and "messages" in update_data:
                            messages = update_data.get("messages", [])
                            if messages and len(messages) > 0:
                                message = messages[0]
                                content = getattr(message, "content", "") if hasattr(message, "content") else str(message)
                                return {
                                    "type": "skill",
                                    "payload": {
                                        "action": "end",
                                        "name": event["name"],
                                        "run_id": event.get("run_id"),
                                        "output": content
                                    }
                                }
                    # 如果无法访问嵌套属性，返回基本结构
                    return {
                        "type": "skill",
                        "payload": {
                            "action": "end",
                            "name": event["name"],
                            "run_id": event.get("run_id"),
                            "output": str(output_data)
                        }
                    }
                else:
                    # 安全地提取输出内容
                    content = ""
                    output_obj = data.get("output", {})
                    if hasattr(output_obj, 'content'):
                        content = output_obj.content
                    else:
                        content = str(output_data)
                        
                    return {
                        "type": "tool",
                        "payload":
                            {
                                "action": "end",
                                "name": event["name"],
                                "run_id": event.get("run_id"),
                                "output": content
                            }
                    }

        except Exception as e:
            err_msg = str(e)
            SysLogger.error(f"SQL Agent运行出错：错误类型：{type(e)}，错误原因{str(e)}")
            SysLogger.exception(f"SQL Agent运行出错：{err_msg}")
            return ({"type": "error",
                     "payload": {"name": "Exception",
                                 "output": f"{err_msg}"}})

    def get_stats(self) -> Dict[str, Any]:
        total_duration = time.perf_counter() - self.metrics["start_time"] if self.metrics["start_time"] is not None else 0
        first_token_time_str = f"{self.metrics['first_token_time']:.4f}" if self.metrics['first_token_time'] is not None else "N/A"
        
        # 构建性能指标数据
        stats_data = {
            "type": "stats",
            "payload": {
                "Total_Input_token": self.metrics["input"],
                "Total_Output_token": self.metrics["output"],
                "Total_Tokens": self.metrics["total_tokens"],
                "First_token_response_time": first_token_time_str,
                "Total_duration": f"{total_duration:.4f}"
            }
        }
        
        # 发送性能指标到 Kafka
        self._send_metrics_to_kafka(stats_data["payload"])
        
        return stats_data
    
    def _send_metrics_to_kafka(self, metrics_payload: Dict[str, Any]):
        """
        将性能指标发送到 Kafka
        """
        try:
            # 获取用户ID
            try:
                user_id = request_user.get()
            except LookupError:
                user_id = "unknown"
            
            # 构建完整的 Kafka 消息
            kafka_message = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "channel": "自助报告2.0",  # 固定值
                "application": "idata",     # 固定值
                "user_id": user_id,         # 用户ID
                "metrics": metrics_payload  # 性能指标数据
            }
            
            # 发送到 Kafka
            self.kafka_manager.send_message(kafka_message)
            SysLogger.info(f"Successfully sent metrics to Kafka: {kafka_message}")
        except Exception as e:
            SysLogger.error(f"Failed to send metrics to Kafka: {e}")
