import time
from typing import Dict, Any

from pydantic.v1.typing import is_none_type

from logger.log import SysLogger
from utils.kafka_manager import KafkaManager
from config.context import request_user
from datetime import datetime

class EventParser:
    def __init__(self):
        self.metrics = {
            "run_id": None,
            "input": 0,
            "output": 0, 
            "total_tokens": 0,
            "interaction_count": 0,
            "start_time": None,
            "first_token_time": None
        }
        self.kafka_manager = KafkaManager()
        # 添加一个标记，确保idata_agg消息只发送一次
        self.agg_stats_sent = False

    def parse_event(self, event):
        try:
            event_type = event["event"]
            data = event.get("data", {})
            run_id = event.get("run_id")
            # SysLogger.info(event)
            if event_type == "on_chain_start":
                if self.metrics["run_id"] is None:
                    self.metrics["run_id"] = run_id
            # 记录模型开始调用的时间
            if event_type == "on_chat_model_start":
                if self.metrics["start_time"] is None:
                    self.metrics["start_time"] = time.perf_counter()
                if self.metrics["run_id"] is None:
                    self.metrics["run_id"] = run_id
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
                    self.metrics["interaction_count"] += 1
                    self.metrics["input"] += usage.get("input_tokens", 0)
                    self.metrics["output"] += usage.get("output_tokens", 0)
                    self.metrics["total_tokens"] += usage.get("total_tokens", 0)

                    # 发送性能指标到 Kafka
                    # 构建完整的 Kafka 消息
                    parent_ids = usage.get("parent_ids", [])
                    # 修复list index out of range错误：检查列表是否为空
                    run_id = parent_ids[0] if isinstance(parent_ids, list) and len(parent_ids) > 0 else "unknown"
                    
                    kafka_message = {
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "channel": "自助报告2.0",  # 固定值
                        "application": "idata",  # 固定值
                        "user_id": request_user.get(),  # 用户ID
                        "run_id":  event.get("run_id"),  # 运行ID
                        "parent_run_id": run_id, # 修复后的运行ID
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    }
                    # 发送到 Kafka
                    print('idata_dtl:',kafka_message)
                    self.kafka_manager = KafkaManager(topic="idata_dtl")
                    self.kafka_manager.send_message(kafka_message)

            if event_type == "on_chat_model_stream":
                ai_chunk = data.get("chunk")
                if ai_chunk and hasattr(ai_chunk, "content"):
                    content = ai_chunk.content
                    if content:
                        return {
                            "type": "text",
                            "payload":
                                {
                                    "run_id": run_id,
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
                                "input": input_data["todos"] if "todos" in input_data else input_data
                            }
                    }
                elif tool_name == "execute_sql" and input_data:
                    return {
                        "type": "tool",
                        "payload":
                            {
                                "action": "start",
                                "name": tool_name,
                                "run_id": run_id,
                                "input": f"```sql\n{input_data['query']}\n```" if "query" in input_data else f"```sql\n{input_data}\n```"
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
                    return {
                        "type": "skill",
                        "payload":
                            {
                                "action": "end",
                                "name": event["name"],
                                "run_id": event.get("run_id"),
                                "output": data.get("output").update.get("messages")[0].content
                            }
                    }
                elif tool_name == "write_todos":
                    return {
                        "type": "plan",
                        "payload":
                            {
                                "action": "end",
                                "name": event["name"],
                                "run_id": event.get("run_id"),
                                "output": data.get("output").update.get("todos")
                            }
                    }
                else:
                    return {
                        "type": "tool",
                        "payload":
                            {
                                "action": "end",
                                "name": event["name"],
                                "run_id": event.get("run_id"),
                                "output": data.get("output").content
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
                "interaction_count": self.metrics["interaction_count"],
                "Total_Input_token": self.metrics["input"],
                "Total_Output_token": self.metrics["output"],
                "Total_Tokens": self.metrics["total_tokens"],
                "First_token_response_time": first_token_time_str,
                "Total_duration": f"{total_duration:.4f}"
            }
        }

        # 只有在还没有发送过idata_agg消息时才发送
        if not self.agg_stats_sent and self.metrics["start_time"] is not None:
            # 发送性能指标到 Kafka
            # 构建完整的 Kafka 消息
            kafka_message = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "channel": "自助报告2.0",  # 固定值
                "application": "idata",  # 固定值
                "user_id": request_user.get(),  # 用户ID
                "run_id": self.metrics["run_id"],  # 运行ID
                "interaction_count": self.metrics["interaction_count"],
                "input_tokens": self.metrics["input"],  # 修正此字段，原来是错误地使用了interaction_count
                "output_tokens": self.metrics["output"],
                "total_tokens": self.metrics["total_tokens"],
                "First_token_response_time": first_token_time_str,
                "Total_duration": f"{total_duration:.4f}",
            }
            # 发送到 Kafka
            print('idata_agg:', kafka_message)
            self.kafka_manager = KafkaManager(topic="idata_agg")
            self.kafka_manager.send_message(kafka_message)
            
            # 标记已经发送过idata_agg消息
            self.agg_stats_sent = True

        return stats_data

