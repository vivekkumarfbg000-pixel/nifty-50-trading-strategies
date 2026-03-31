import json
import logging
from datetime import datetime
from typing import Dict, Any
from config import config

logger = logging.getLogger("Telemetry")

class Telemetry:
    """Event logging and telemetry collection"""
    
    def __init__(self):
        self.events = []
    
    def log_event(self, event_type: str, data: Dict[str, Any], username: str = "system"):
        """Log an event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "username": username,
            "data": data,
        }
        self.events.append(event)
        logger.debug(f"Event: {event_type} | {data}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get telemetry summary"""
        event_counts = {}
        for evt in self.events:
            evt_type = evt["event_type"]
            event_counts[evt_type] = event_counts.get(evt_type, 0) + 1
        
        return {
            "total_events": len(self.events),
            "event_types": event_counts,
            "last_10": self.events[-10:] if self.events else [],
        }
    
    def export_json(self, filename: str = None):
        """Export events to JSON"""
        if filename is None:
            filename = f"telemetry_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, "w") as f:
            json.dump(self.events, f, indent=2)
        
        logger.info(f"Exported {len(self.events)} events to {filename}")
        return filename

telemetry = Telemetry()
