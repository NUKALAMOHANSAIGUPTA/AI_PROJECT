import collections
import random
from dataclasses import dataclass
from enum import Enum

class BookingStatus(Enum):
    AVAILABLE = "Available"
    CONFIRMED = "Confirmed (Full Seat)"
    RAC_SHARED = "RAC (Shared Seat)"
    WAITING = "Waiting List"

class PassengerType(Enum):
    NORMAL = "Normal"
    TATKAL = "Tatkal"

class Gender(Enum):
    MALE = "Male"
    FEMALE = "Female"

@dataclass
class Passenger:
    name: str
    p_type: PassengerType
    gender: Gender
    prefers_rac: bool
    seat_number: int = None
    pnr: str = None
    status: BookingStatus = BookingStatus.WAITING
    
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.p_type.value,
            "gender": self.gender.value,
            "prefers_rac": self.prefers_rac,
            "seat_number": self.seat_number,
            "pnr": self.pnr,
            "status": self.status.value
        }

class SeatNode:
    def __init__(self, seat_number):
        self.seat_number = seat_number
        self.status = BookingStatus.AVAILABLE
        self.occupants = [] 
        self.left = None
        self.right = None
        
    def to_dict(self):
        return {
            "seat_number": self.seat_number,
            "status": self.status.value,
            "occupants": [p.to_dict() for p in self.occupants],
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None
        }

class SeatTree:
    def __init__(self):
        self.root = None
        self.count = 0

    def add_seat_node(self, seat_id):
        new_node = SeatNode(seat_id)
        self.count += 1
        if not self.root:
            self.root = new_node
            return new_node
        q = collections.deque([self.root])
        while q:
            curr = q.popleft()
            if not curr.left:
                curr.left = new_node
                break
            else: q.append(curr.left)
            if not curr.right:
                curr.right = new_node
                break
            else: q.append(curr.right)
        return new_node

class IRCTCSystem:
    def __init__(self, initial_pool):
        self.seat_tree = SeatTree()
        self.active_passengers = [] 
        self.waiting_list = collections.deque() 
        self.tatkal_window_open = False
        self.available_seat_ids = sorted(initial_pool)

    def generate_pnr(self):
        return "".join([str(random.randint(0, 9)) for _ in range(10)])

    def process_bulk_booking(self, passengers):
        logs = []
        for p in passengers:
            p.pnr = self.generate_pnr()
            
            if self.available_seat_ids:
                sid = self.available_seat_ids.pop(0)
                node = self.seat_tree.add_seat_node(sid)
                node.status = BookingStatus.CONFIRMED
                node.occupants.append(p)
                p.seat_number = sid
                p.status = BookingStatus.CONFIRMED
                self.active_passengers.append(p)
                logs.append(f"CONFIRMED | PNR: {p.pnr} | {p.name} | Seat: {p.seat_number} (Full)")

            elif p.prefers_rac and self._try_proactive_merge(p, logs):
                continue

            else:
                p.status = BookingStatus.WAITING
                if p.p_type == PassengerType.TATKAL:
                    idx = 0
                    for x in self.waiting_list:
                        if x.p_type == PassengerType.TATKAL: idx += 1
                        else: break
                    self.waiting_list.insert(idx, p)
                else:
                    self.waiting_list.append(p)
                pref = "RAC OK" if p.prefers_rac else "FULL SEAT ONLY"
                logs.append(f"WAITING | PNR: {p.pnr} | {p.name} | Status: {pref}")
        return logs

    def _try_proactive_merge(self, new_p, logs):
        if not self.seat_tree.root: return False
        q = collections.deque([self.seat_tree.root])
        while q:
            curr = q.popleft()
            if len(curr.occupants) == 1:
                host = curr.occupants[0]
                if host.prefers_rac and host.gender == new_p.gender:
                    curr.occupants.append(new_p)
                    curr.status = BookingStatus.RAC_SHARED
                    new_p.seat_number = curr.seat_number
                    new_p.status = BookingStatus.RAC_SHARED
                    self.active_passengers.append(new_p)
                    logs.append(f"RAC MERGE | PNR: {new_p.pnr} | {new_p.name} | Sharing Seat {new_p.seat_number} with {host.name}")
                    return True
            if curr.left: q.append(curr.left)
            if curr.right: q.append(curr.right)
        return False

    def cancel_by_name(self, name):
        name_clean = name.strip().lower()
        target = next((p for p in self.active_passengers if p.name.lower() == name_clean), None)
        logs = []
        
        if not target:
            target = next((p for p in self.waiting_list if p.name.lower() == name_clean), None)
            if target:
                self.waiting_list.remove(target)
                logs.append(f"CANCELLED: {target.name} removed from Waiting List.")
                return logs
            logs.append(f"Error: Name '{name}' not found.")
            return logs

        old_seat = target.seat_number
        self.active_passengers.remove(target)
        remaining_p = self._remove_from_tree(old_seat, target)
        logs.append(f"CANCELLED: {target.name} (Freed Seat {old_seat})")

        if remaining_p:
            remaining_p.status = BookingStatus.CONFIRMED
            logs.append(f"PROMOTED: {remaining_p.name} is now Confirmed (Full Seat {old_seat})")
        else:
            if not self.waiting_list:
                self.available_seat_ids.append(old_seat)
                self.available_seat_ids.sort()
            else:
                self._promote_next_pair_logic(old_seat, logs)
        return logs

    def _remove_from_tree(self, sid, target_p):
        q = collections.deque([self.seat_tree.root])
        while q:
            curr = q.popleft()
            if curr.seat_number == sid:
                if target_p in curr.occupants: curr.occupants.remove(target_p)
                if not curr.occupants:
                    curr.status = BookingStatus.AVAILABLE
                    return None
                else:
                    curr.status = BookingStatus.CONFIRMED
                    return curr.occupants[0]
            if curr.left: q.append(curr.left)
            if curr.right: q.append(curr.right)

    def _promote_next_pair_logic(self, seat_num, logs):
        p1 = self.waiting_list.popleft()
        if p1.prefers_rac:
            p2 = None
            for i in range(len(self.waiting_list)):
                cand = self.waiting_list[i]
                if cand.prefers_rac and cand.gender == p1.gender:
                    p2 = cand
                    break
            if p2:
                self.waiting_list.remove(p2)
                self._update_node(seat_num, BookingStatus.RAC_SHARED, [p1, p2])
                p1.status = p2.status = BookingStatus.RAC_SHARED
                p1.seat_number = p2.seat_number = seat_num
                self.active_passengers.extend([p1, p2])
                logs.append(f"PROMOTED: {p1.name} & {p2.name} sharing RAC Seat {seat_num}")
                return

        self._update_node(seat_num, BookingStatus.CONFIRMED, [p1])
        p1.status = BookingStatus.CONFIRMED
        p1.seat_number = seat_num
        self.active_passengers.append(p1)
        logs.append(f"PROMOTED: {p1.name} assigned FULL Seat {seat_num}")

    def _update_node(self, sid, status, occupants):
        q = collections.deque([self.seat_tree.root])
        while q:
            curr = q.popleft()
            if curr.seat_number == sid:
                curr.status = status
                curr.occupants = occupants
                return
            if curr.left: q.append(curr.left)
            if curr.right: q.append(curr.right)

    def get_state(self):
        # We also need flattening for simple UI consumption
        nodes = []
        def traverse(node):
            if not node: return
            traverse(node.left)
            nodes.append(node.to_dict())
            traverse(node.right)
        if self.seat_tree.root:
            traverse(self.seat_tree.root)
            
        nodes = sorted(nodes, key=lambda x: x["seat_number"])

        return {
            "available_seat_count": len(self.available_seat_ids),
            "available_seats": list(self.available_seat_ids),
            "tatkal_open": self.tatkal_window_open,
            "active_passengers": [p.to_dict() for p in self.active_passengers],
            "waiting_list": [p.to_dict() for p in self.waiting_list],
            "seats": nodes
        }
