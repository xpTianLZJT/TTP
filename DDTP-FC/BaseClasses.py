import math
from collections import defaultdict

#数据输入分类
class Node:#节点
     def __init__(self, node_id, storage_cap, run_dir,node_attr, node_time):# node_seq_no):#(实例本身，节点编号，节点序列号) self代表类的实例，而非类）
        self.node_id = node_id           #车站编号        
        self.node_direction=run_dir
        self.node_attr=node_attr
        self.node_time=node_time
        
        self.storage_cap=storage_cap   #=0 为不具有解编的普通车站 0<storage_cap<=6为具有具有解编的普通车站  storage_cap>6为折返站
        
        self.outgoing_link_list = []     #输出路段列表
        self.incoming_link_list = []     #输入路段列表


class Link:#路段
    def __init__(self, link_id, link_seq_no, from_node_id, to_node_id, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,from_time):#定义路段信息
        self.link_id = link_id                   #路段编号
        self.link_seq_no = link_seq_no           # 路段序列号
        self.from_node_id = from_node_id         #从节点id
        self.to_node_id = to_node_id             #到节点Id
        self.from_node_seq_no = from_node_seq_no #起始节点序列号
        self.to_node_seq_no = to_node_seq_no     #终到节点序列号
        self.link_cost = link_cost               #路段成本
        self.link_travel_time = link_travel_time #路段旅行时间
        self.from_time=from_time
        
        self.link_direction=run_dir #0 no direction; 1 is up; 2 is down
        self.link_cap=link_cap
        self.link_type=link_type #(-1)-passenger virtual arcs; 0-train virtual arcs;1-station arcs;2-running arc;3-others
        
        self.start_time=None
        self.end_time=None
'''
   弧	                标号(link_type)
---------------------------------------  
列车虚拟弧			     vt
乘客虚拟弧			     vp
乘客虚拟直通弧		     vv
列车运行弧-上行		     ur
列车运行弧-下行			 dr
列车折返弧-上行→下行     tud
列车折返弧-下行→上行     tdu
列车闲置/等待弧	         idl
---------------------------------------
'''

class Agent:#demand
    def __init__(self, origin_node_id, destination_node_id, time_threshold):
        self.origin_node_id = origin_node_id#起始点编号
        self.destination_node_id = destination_node_id#终点编号
        self.time_threshold = time_threshold


class Section:#路段
    def __init__(self, section_id, from_node_id, to_node_id,run_direction,run_time,belong_OD_list,minService,maxService,demand_vol,later_num_unit,sec_dis):#定义路段信息
        self.section_id = section_id           
        self.from_node_id = from_node_id         #从节点id
        self.to_node_id = to_node_id             #到节点Id
        self.run_direction=run_direction  #1为上行，-1为下行
        self.run_time=run_time
        self.belong_OD_list=belong_OD_list
        self.minService=minService
        self.maxService=maxService
        self.max_train_unit=0
        self.demand_vol=demand_vol
        self.later_num_unit={}
        self.sec_dis=sec_dis
      

class Network:#路网
    def __init__(self):
        self.node_list = [] #路网节点列表 时空
        self.link_list = [] #路网路段列表 时空        
        self.section_list=[] #物理区间
        self.sec_index_to_no_dict = {}
        
        # self.node_id_to_no_dict = {}
        # self.node_no_to_id_dict = {}
        # self.link_id_to_no_dict = {}
        # self.link_no_to_id_dict = {}        
        # self.node_label_cost = []#节点标签成本
        # # stores the current total travel time when traversing from the source node to all other node存储从源节点遍历到所有其他节点时的当前总行程时间
        # self.node_traverse_time = [] 节点遍历时间
        self.node_predecessor = []#前一个节点
        self.link_predecessor = []#前一条路段
        
        self.node_index_to_no_dict = {}
        self.link_index_to_no_dict = {}
        self.node_no_dict_to_index = {}
        self.link_no_dict_to_index = {}
        self.link_cap=0
        
        
        self.stor_station_list=[] #可以解编的车站
        self.turnback_station_list=[] #折返车站
        self.station_storage={}
        self.max_start_unit={}
        
        self.station_arc_run={}  #每个车站的运行弧
        
        self.OD_direction={}
        self.OD_station={}
        
        self.OD_running_time={}
        
        self.end_unit={}
        self.init_unit={}
        
        self.vir_arc_pax={}  #每个OD对的虚拟arc
        self.ori_arc_run=defaultdict(list)  #每个OD对起始站离开时间t的运行arc
        
        self.uncouple_arc={}
        self.couple_arc={}
        self.return_arc={}
        self.transfer_arc={}


class Demand:
    def __init__(self):
        self.demand_dic = {}
        self.demand_OD={}
        self.demand_accum={}
        self.OD_list=[]
        self.demand_max={}
    
class Param:
    def __init__(self):    
        # ##small example      
        # self.rolling_flag=0  #1 表示起始时段  2 表示中间时段  3 表示末尾时段  0 表示完整的整个时段
        # self.min_time=0
        # self.max_time=150   #the study horizon time [0,maxTime] 6:00-23:00
        # self.min_wait_time=0 #区间运行时间已经考虑了停站时间，此参数务必为零
        # # self.max_wait_time=2
        # self.safe_interval=2
        # self.max_interval=10     
        # self.transfer_time=3
        # self.num_station=5
        # self.max_unit=66
        # self.max_unit_to_singletrain=6
        # self.single_cap=30
        # self.max_pax_cap=50000 #大于总需求数
        # self.vitual_pax_cost=1000  #乘客未上车的剩余成本
        # self.wait_pax_cost=1  #单个乘客等待1分钟的成本
        # self.weight_train=3  #e1
        # self.weight_pax=1    #e2    
        
 
        ##big example and comparison example
        self.rolling_flag=3  #1 表示起始时段  2 表示中间时段  3 表示末尾时段  0 表示完整的整个时段
        self.min_time=960
        self.max_time=1020    #the study horizon time [0,maxTime] 6:00-23:00
        self.min_wait_time=0 #区间运行时间已经考虑了停站时间，此参数务必为零
        # self.max_wait_time=2
        self.safe_interval=2
        self.max_interval=10    
        self.transfer_time=3
        self.num_station=12
        self.max_unit=64
        self.max_unit_to_singletrain=2
        self.single_cap=900
        self.max_pax_cap=200000 #大于总需求数
        self.vitual_pax_cost=1000  #乘客未上车的剩余成本
        self.wait_pax_cost=1  #单个乘客等待1分钟的成本
        self.weight_train=3
        self.weight_pax=1


        # ##Bender comparative examples
        # self.rolling_flag=1  #1 表示起始时段  2 表示中间时段  3 表示末尾时段  0 表示完整的整个时段
        # self.min_time=0
        # self.max_time=72   #the study horizon time [0,maxTime] 6:00-23:00
        # self.min_wait_time=0 #区间运行时间已经考虑了停站时间，此参数务必为零
        # # self.max_wait_time=2
        # self.safe_interval=2
        # self.max_interval=10       
        # self.transfer_time=3
        # self.num_station=4
        # self.max_unit=60
        # self.max_unit_to_singletrain=2
        # self.single_cap=900
        # self.max_pax_cap=200000 #大于总需求数
        # self.vitual_pax_cost=1000  #乘客未上车的剩余成本
        # self.wait_pax_cost=1  #单个乘客等待1分钟的成本
        # self.weight_train=3
        # self.weight_pax=1


        # self.key_OD_list=[]
        self.key_OD_list=[(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(0,7),(0,8),(0,9),(0,10),(0,11),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0),(7,0),(8,0),(9,0),(10,0),(11,0)]
        # self.key_OD_list=[(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(0,7),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0),(7,0)]
        # self.key_OD_list=[(0,1),(0,2),(0,3),(1,0),(2,0),(3,0)]

        #(un)coupling parameters
        self.couple_time=1
        self.uncouple_time=1
        self.uncouple_to_storage_time=2
        self.weight_sta_opera=0.01

        # self.level_comosition=[3,4,5,6]   #small exp
        self.level_comosition=[1,2]  #big exp
        self.cost_composition={}  #
        for i in self.level_comosition:
            self.cost_composition[i]=(2.049+0.37*pow(i*self.single_cap,0.5))*1
            # print(i,self.cost_composition[i])
        # input()
        
        self.OD_dir={}
        
        #for OD pairs
        self.earliest_time={}
        self.latest_time={}
        #for trains
        self.train_early_time={}
        self.train_latest_time={}       
       
