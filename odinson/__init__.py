"""Odinson — low-cost IoT vibration & seismic monitoring platform.

Arduino + MPU6050  ->  Python gateway (serial/mock)  ->  local UI + SQLite/CSV
                                                        ->  AWS (DynamoDB, SNS,
                                                            CloudWatch, S3, IoT Core)
"""

__version__ = "3.0.0"
