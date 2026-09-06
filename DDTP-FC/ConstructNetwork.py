import csv #读写调查CSV文件
import os
from BaseClasses import Node, Section, Link, Agent, Network, Demand, Param
from utils import _convert_str_to_int, _convert_str_to_float
import math

def read_nodes(input_dir, network):#读取节点（输入目录，网络）
    # Read node info读取节点信息
    print('Read node.csv')
    print(network)
    # input()
    with open(input_dir + '/node.csv', 'r', encoding='utf-8') as fp:
        reader = csv
        reader = csv.DictReader(fp)
        
        node_seq_no = 0        
        for line in reader:
            node_id = _convert_str_to_int(line['node_id'])
            if node_id is None:
                continue
            
            storage_cap = _convert_str_to_int(line['storage_cap'])
            network.station_storage[node_id]=storage_cap
            if storage_cap is None:
                continue  
            if storage_cap>param.max_unit_to_singletrain:
                network.turnback_station_list.append(node_id)
            if storage_cap>0:
                network.stor_station_list.append(node_id)
                
            num_init_unit_up = _convert_str_to_int(line['init_unit_up'])
            network.init_unit[1,node_id]=num_init_unit_up
            if num_init_unit_up is None:
                continue 

            num_init_unit_down = _convert_str_to_int(line['init_unit_down'])
            network.init_unit[2,node_id]=num_init_unit_down
            if num_init_unit_down is None:
                continue
                
            num_end_unit_up = _convert_str_to_int(line['end_unit_up'])
            network.end_unit[1,node_id]=num_end_unit_up
            if num_end_unit_up is None:
                continue

            num_end_unit_down = _convert_str_to_int(line['end_unit_down'])
            network.end_unit[2,node_id]=num_end_unit_down
            if num_end_unit_down is None:
                continue
            
            for t in range(param.max_time):
                #updirection nodes
                node = Node(node_id, storage_cap, 1, 1, t)
                network.node_list.append(node)
                index=(node_id,t,1,1)
                #(node_id,t,1,1) 第一位是车站，第二位是时间，第三位是上下行（1上，2下），第四位是点的属性（1离开，2耦合，3解编）
                network.node_index_to_no_dict[index] = node_seq_no
                network.node_no_dict_to_index[node_seq_no]=index
                node_seq_no += 1
                
                if node_id in network.stor_station_list and node_id != 0 and node_id != param.num_station-1:
                    # print(node_id,"*-*-*")
                    # input()     
                    
                    node = Node(node_id, storage_cap, 1, 2, t)
                    network.node_list.append(node)
                    index=(node_id,t,1,2)                    
                    network.node_index_to_no_dict[index] = node_seq_no
                    network.node_no_dict_to_index[node_seq_no]=index
                    node_seq_no += 1
                    
                    node = Node(node_id, storage_cap, 1, 3, t)
                    network.node_list.append(node)
                    index=(node_id,t,1,3)                
                    network.node_index_to_no_dict[index] = node_seq_no
                    network.node_no_dict_to_index[node_seq_no]=index
                    node_seq_no += 1
                
                #downdirection nodes
                node = Node(node_id, storage_cap, 2,1, t)
                network.node_list.append(node)
                index=(node_id,t,2,1)           
                network.node_index_to_no_dict[index] = node_seq_no 
                network.node_no_dict_to_index[node_seq_no]=index
                node_seq_no += 1
                
                if node_id in network.stor_station_list and node_id != 0 and node_id != param.num_station-1:
                    # print(node_id,"*-*-*")
                    # input()     
                    node = Node(node_id, storage_cap, 2,2, t)
                    network.node_list.append(node)
                    index=(node_id,t,2,2)           
                    network.node_index_to_no_dict[index] = node_seq_no 
                    network.node_no_dict_to_index[node_seq_no]=index
                    node_seq_no += 1 
                    
                    node = Node(node_id, storage_cap, 2,3, t)
                    network.node_list.append(node)
                    index=(node_id,t,2,3)           
                    network.node_index_to_no_dict[index] = node_seq_no 
                    network.node_no_dict_to_index[node_seq_no]=index
                    node_seq_no += 1            
     
    
    # print(network.stor_station_list)
    # print(network.turnback_station_list)
    # input()
    
    #starting node for trains
    node = Node(-1, param.max_unit, -1,-1, -1)
    index=(-1,-1,-1,-1)
    network.node_index_to_no_dict[index] = node_seq_no
    network.node_no_dict_to_index[node_seq_no]=index    
    network.node_list.append(node)
    node_seq_no += 1        
    
    #ending node for trains
    node = Node(-2, param.max_unit, -2,-2, -2)
    index=(-2,-2,-2,-2)
    network.node_index_to_no_dict[index] = node_seq_no
    network.node_no_dict_to_index[node_seq_no]=index    
    network.node_list.append(node)
    node_seq_no += 1
    
    #origin and destination nodes for passengers
    for s in range(param.num_station):
        index=(-100-s,-100-s,-100-s,-100-s)
        network.node_index_to_no_dict[index] = node_seq_no
        network.node_no_dict_to_index[node_seq_no]=index        
        node = Node(-100-s, 0, -3,-3, -3)
        network.node_list.append(node)
        node_seq_no += 1
    
        for sp in range(param.num_station):
            if s!=sp:
                demand.OD_list.append((s,sp))
    
        for run_dir in [1,2]:
            network.station_arc_run[s,run_dir]=[]
            network.uncouple_arc[s,run_dir]=[]
            network.couple_arc[s,run_dir]=[]
            network.transfer_arc[s,run_dir]=[]
            network.return_arc[s,run_dir]=[]
    
    print(f"Number of nodes is: {node_seq_no}",f"Number of stations:{param.num_station}")
    network.node_size = node_seq_no
    print(node_seq_no)
    
    


def read_links(input_dir, network):#定义读取路段信息
    # Read link info读取路段信息
    print('\nRead link.csv')

    with open(input_dir + '/link.csv', 'r', encoding='utf-8') as fp:
        reader = csv.DictReader(fp)        
        for line in reader:
            link_id = _convert_str_to_int(line['link_id'])
            if link_id is None:
                continue

            from_node_id = _convert_str_to_int(line['from_node_id'])
            if from_node_id is None:
                continue

            to_node_id = _convert_str_to_int(line['to_node_id'])
            if to_node_id is None:
                continue

            segment_travel_time = _convert_str_to_int(line['link_travel_time'])
            if to_node_id is None:
                continue  

            minService = _convert_str_to_int(line['minService'])
            if minService is None:
                continue                 

            maxService = _convert_str_to_int(line['maxService'])
            if maxService is None:
                continue  
            
            secDis = _convert_str_to_float(line['secDis'])
            if secDis is None:
                continue                
                         
            run_dir=1  #updirection 
            if from_node_id>to_node_id:                                  
                run_dir=2  #downdirection 
                        
            belong_OD_list=[]
            for w in demand.OD_list:
                if w[0]<=from_node_id<to_node_id<=w[1] or w[1]<=to_node_id<from_node_id<=w[0]:
                    belong_OD_list.append(w)
            
            # print(from_node_id,to_node_id,belong_OD_list)
            # input()
            
            section=Section(link_id,from_node_id,to_node_id,run_dir,segment_travel_time,belong_OD_list,minService,maxService,0,0,secDis)
            network.section_list.append(section)
            network.sec_index_to_no_dict[run_dir,from_node_id]=section 
            # print(run_dir,from_node_id)
            # input()
    
    link_seq_no = 0
    calculating_time_range()
    
    for s in range(param.num_station):        
        if s in network.stor_station_list and s !=0 and s != param.num_station-1:                    
            # print(s,"*---*")
            for run_dir in [1,2]:
                r_dir=2 if run_dir==1 else 1
                for t in range(param.max_time):  
                    #constructing transfer arcs for storage stations  折返弧 非起终车站
                    if s in network.turnback_station_list:
                        from_index=(s,t,run_dir,2)
                        tp=t+param.transfer_time
                        if tp<param.max_time:
                            to_index=(s,tp,r_dir,2)
                            from_node_seq_no=network.node_index_to_no_dict[from_index]
                            to_node_seq_no=network.node_index_to_no_dict[to_index]
                            link_cost=tp-t
                            link_travel_time=link_cost
                            link_cap=param.max_unit_to_singletrain
                            index=(from_node_seq_no,to_node_seq_no)
                            network.link_index_to_no_dict[index]=link_seq_no
                            # network.link_no_dict_to_index[link_seq_no]=index
                            link_type='tud' if run_dir==1 else 'tdu'
                            link = Link(link_id, link_seq_no, s, s, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,t)                    
                            link.start_time=t
                            link.end_time=tp
                            
                            network.link_list.append(link)  
                            network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                            network.node_list[to_node_seq_no].incoming_link_list.append(link)  
                            
                            network.transfer_arc[s,run_dir].append(link_seq_no)
                            
                            link_seq_no += 1
                        
                    #constructing idling arcs at storage tracks (耦合点之间的等待弧)   非起终车站   
                    from_index=(s,t,run_dir,2)
                    tp=t+1
                    if tp<param.max_time:
                        to_index=(s,tp,run_dir,2)
                        from_node_seq_no=network.node_index_to_no_dict[from_index]
                        to_node_seq_no=network.node_index_to_no_dict[to_index]                        
                        link_cost=tp-t
                        link_travel_time=link_cost
                        link_cap=network.station_storage[s]
                        index=(from_node_seq_no,to_node_seq_no)
                        network.link_index_to_no_dict[index]=link_seq_no
                        link_type='idl'
                        link = Link(link_id, link_seq_no, s, s, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,t)                    
                        link.start_time=t
                        link.end_time=tp
                        
                        network.link_list.append(link)
                        network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                        network.node_list[to_node_seq_no].incoming_link_list.append(link)                         
                        link_seq_no += 1
                
                    #constructing (un)coupling arcs at storage tracks   非起终车站   
                    from_index=(s,t,run_dir,3)
                    tp=t+param.uncouple_time
                    if tp<param.max_time:
                        to_index=(s,tp,run_dir,1)
                        from_node_seq_no=network.node_index_to_no_dict[from_index]
                        to_node_seq_no=network.node_index_to_no_dict[to_index]                        
                        link_cost=tp-t
                        link_travel_time=link_cost
                        link_cap=param.max_unit_to_singletrain
                        index=(from_node_seq_no,to_node_seq_no)
                        network.link_index_to_no_dict[index]=link_seq_no
                        link_type='ucd'
                        link = Link(link_id, link_seq_no, s, s, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,t)                    
                        link.start_time=t
                        link.end_time=tp
                        
                        network.link_list.append(link)
                        network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                        network.node_list[to_node_seq_no].incoming_link_list.append(link)                         
                        
                        network.uncouple_arc[s,run_dir].append(link_seq_no)
                        
                        link_seq_no += 1                        

                    #constructing return_to_storagetrack arcs at storage tracks   非起终车站   
                    from_index=(s,t,run_dir,3)
                    tp=t+param.uncouple_to_storage_time
                    if tp<param.max_time:
                        to_index=(s,tp,run_dir,2)
                        from_node_seq_no=network.node_index_to_no_dict[from_index]
                        to_node_seq_no=network.node_index_to_no_dict[to_index]                        
                        link_cost=tp-t
                        link_travel_time=link_cost
                        link_cap=param.max_unit_to_singletrain
                        index=(from_node_seq_no,to_node_seq_no)
                        network.link_index_to_no_dict[index]=link_seq_no
                        link_type='ucr'
                        link = Link(link_id, link_seq_no, s, s, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,t)                    
                        link.start_time=t
                        link.end_time=tp
                        
                        network.link_list.append(link)
                        network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                        network.node_list[to_node_seq_no].incoming_link_list.append(link)                         
                        
                        network.return_arc[s,run_dir].append(link_seq_no)
                        
                        link_seq_no += 1 

                    #constructing coupling arcs at storage tracks   非起终车站   
                    from_index=(s,t,run_dir,2)
                    tp=t+param.couple_time
                    if tp<param.max_time:
                        to_index=(s,tp,run_dir,1)
                        from_node_seq_no=network.node_index_to_no_dict[from_index]
                        to_node_seq_no=network.node_index_to_no_dict[to_index]                        
                        link_cost=tp-t
                        link_travel_time=link_cost
                        link_cap=param.max_unit_to_singletrain
                        index=(from_node_seq_no,to_node_seq_no)
                        network.link_index_to_no_dict[index]=link_seq_no
                        link_type='cod'
                        link = Link(link_id, link_seq_no, s, s, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,t)                    
                        link.start_time=t
                        link.end_time=tp
                        
                        network.link_list.append(link)
                        network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                        network.node_list[to_node_seq_no].incoming_link_list.append(link) 

                        network.couple_arc[s,run_dir].append(link_seq_no)
                        
                        link_seq_no += 1
                        
            
        if s==0 or s == param.num_station-1:
            # print(s,"****")
            # input()
            run_dir=1 if s==param.num_station-1 else 2
            r_dir=2 if run_dir==1 else 1
            for t in range(param.max_time):
                #constructing transfer arcs for storage stations  折返弧    起终车站             
                from_index=(s,t,run_dir,1)
                tp=t+param.transfer_time
                if tp<param.max_time:
                    to_index=(s,tp,r_dir,1)
                    from_node_seq_no=network.node_index_to_no_dict[from_index]
                    to_node_seq_no=network.node_index_to_no_dict[to_index]
                    link_cost=tp-t
                    link_travel_time=link_cost
                    link_cap=param.max_unit_to_singletrain
                    index=(from_node_seq_no,to_node_seq_no)
                    network.link_index_to_no_dict[index]=link_seq_no
                    # network.link_no_dict_to_index[link_seq_no]=index
                    link_type='tud' if run_dir==1 else 'tdu'
                    link = Link(link_id, link_seq_no, s, s, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,t)                    
                    link.start_time=t
                    link.end_time=tp
                    
                    network.link_list.append(link)  
                    network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                    network.node_list[to_node_seq_no].incoming_link_list.append(link)

                    network.transfer_arc[s,run_dir].append(link_seq_no)
                    
                    link_seq_no += 1                

                #constructing idling arcs at storage tracks (耦合点之间的等待弧) 起终车站
                from_index=(s,t,r_dir,1)
                tp=t+1
                if tp<param.max_time:
                    to_index=(s,tp,r_dir,1)
                    from_node_seq_no=network.node_index_to_no_dict[from_index]
                    to_node_seq_no=network.node_index_to_no_dict[to_index]                        
                    link_cost=tp-t
                    link_travel_time=link_cost
                    link_cap=network.station_storage[s]
                    index=(from_node_seq_no,to_node_seq_no)
                    network.link_index_to_no_dict[index]=link_seq_no
                    link_type='idl'
                    link = Link(link_id, link_seq_no, s, s, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,t)                    
                    link.start_time=t
                    link.end_time=tp
                    
                    network.link_list.append(link)
                    network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                    network.node_list[to_node_seq_no].incoming_link_list.append(link)                         
                    link_seq_no += 1
    
    # print(len(network.return_arc[s,run_dir]))
    # input()
    
    for sec in network.section_list:
        link_id=sec.section_id
        from_node_id = sec.from_node_id
        to_node_id = sec.to_node_id
        segment_travel_time =sec.run_time
        run_dir=sec.run_direction 
        
        #constructing running arcs
        for v_type in range(1,4):
            if run_dir==1 and to_node_id==param.num_station-1 and v_type!=1:
                continue
            # if run_dir==1 and from_node_id==0 and v_type!=1:
                # continue
            if run_dir==2 and to_node_id==0 and v_type!=1:
                continue
            # if run_dir==2 and from_node_id==param.num_station-1 and v_type!=1:
                # continue
            if to_node_id not in network.stor_station_list and v_type!=1:
                continue
            
            for t in range(param.max_time):                
                from_index=(from_node_id,t,run_dir,1)
                tp=t+param.min_wait_time+segment_travel_time
                if tp<param.max_time:
                    to_index=(to_node_id,tp,run_dir,v_type)
                    from_node_seq_no=network.node_index_to_no_dict[from_index]
                    to_node_seq_no=network.node_index_to_no_dict[to_index]                    
                    link_cost=tp-t
                    link_travel_time=link_cost
                    link_cap=param.max_unit_to_singletrain
                    index=(from_node_seq_no,to_node_seq_no)                  
                    network.link_index_to_no_dict[index]=link_seq_no
                    network.link_no_dict_to_index[link_seq_no]=index
                    link_type='ur' if run_dir==1 else 'dr'                
                    link = Link(link_id, link_seq_no, from_node_id, to_node_id, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,t)                    
                    link.start_time=t
                    link.end_time=tp
                    
                    network.link_list.append(link)                
                    network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                    network.node_list[to_node_seq_no].incoming_link_list.append(link)                
                    
                    network.station_arc_run[from_node_id,run_dir].append(link_seq_no)
                    
                    # if link_seq_no==919:
                        # print(link_seq_no)
                        # input()
                    
                    for w in demand.OD_list:
                        rd=1 if w[0]<w[1] else 2
                        if rd==run_dir and w[0]==from_node_id:
                            if param.earliest_time[w,w[0]]<=t<=param.latest_time[w,w[0]]:
                                for tpp in range(t,param.latest_time[w,w[0]]+1):
                                    network.ori_arc_run[w,tpp].append(link_seq_no)
                    
                    link_seq_no += 1

        
    #constructing virtual arcs for trains
    for s in network.turnback_station_list:
        #pull in arc
        temp_dir=[]
        if s==0:
            temp_dir.append(1)
        elif s==param.num_station-1:
            temp_dir.append(2)
        else:
            temp_dir.append(1)
            temp_dir.append(2)
            
        for r_dir in temp_dir:
            from_node_id=-1
            to_node_id=s
            from_index=(-1,-1,-1,-1)
            v_type=1 if (s==0 or s==param.num_station-1) else 2
            to_index=(s,0,r_dir,v_type) #要核实0时刻是起始时刻
            from_node_seq_no=network.node_index_to_no_dict[from_index]
            to_node_seq_no=network.node_index_to_no_dict[to_index]                    
            link_cost=0
            link_travel_time=link_cost
            link_cap=network.station_storage[s]
            index=(from_node_seq_no,to_node_seq_no)
            network.link_index_to_no_dict[index]=link_seq_no
            link_type='vt'
            link = Link(link_id, link_seq_no, from_node_id, to_node_id, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,r_dir,-1)                    
            link.start_time=-1
            link.end_time=0
            
            network.link_list.append(link)                
            network.node_list[from_node_seq_no].outgoing_link_list.append(link)
            network.node_list[to_node_seq_no].incoming_link_list.append(link)                
            link_seq_no += 1

        #pull out arc
        for r_dir in temp_dir:
            from_node_id=s
            to_node_id=-2
            v_type=1 if (s==0 or s==param.num_station-1) else 2
            from_index=(s,param.max_time-1,r_dir,v_type)
            to_index=(-2,-2,-2,-2)
            from_node_seq_no=network.node_index_to_no_dict[from_index] 
            to_node_seq_no=network.node_index_to_no_dict[to_index]                     
            link_cost=0
            link_travel_time=link_cost
            link_cap=network.station_storage[s]
            index=(from_node_seq_no,to_node_seq_no)
            network.link_index_to_no_dict[index]=link_seq_no
            link_type='vt'
            link = Link(link_id, link_seq_no, from_node_id, to_node_id, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,r_dir,-2)                    
            link.start_time=(param.max_time-1)
            link.end_time=-2
            
            network.link_list.append(link)                
            network.node_list[from_node_seq_no].outgoing_link_list.append(link)
            network.node_list[to_node_seq_no].incoming_link_list.append(link) 
            # print(link_seq_no)
            # input()
            link_seq_no += 1            

    #constructing vitual arcs for passengers
    for s in range(param.num_station): 
        for run_dir in [1,2]:#=1 is up; =2 is down                
            from_node_id_ori=-s-100
            to_node_id_ori=s
            
            from_node_id_des=s
            to_node_id_des=-s-100
            
            from_index_ori=(from_node_id_ori,from_node_id_ori,from_node_id_ori,from_node_id_ori)
            to_index_des=(to_node_id_des,to_node_id_des,to_node_id_des,to_node_id_des)
            for t in range(param.max_time):
                #vitual arcs from passenger vitual to stations
                to_index_ori=(to_node_id_ori,t,run_dir,1)   

                from_node_seq_no=network.node_index_to_no_dict[from_index_ori]                
                to_node_seq_no=network.node_index_to_no_dict[to_index_ori] 
                
                link_cost=0
                link_travel_time=link_cost
                link_cap=param.max_pax_cap
                index=(from_node_seq_no,to_node_seq_no)
                network.link_index_to_no_dict[index]=link_seq_no
                link_type='vp'
                link = Link(link_id, link_seq_no, from_node_id_ori, to_node_id_ori, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,-100)                    
                link.start_time=-100
                link.end_time=t
                
                network.link_list.append(link)   
                # print(link_seq_no,to_node_id_ori,t,"test...")
                # input()
                network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                network.node_list[to_node_seq_no].incoming_link_list.append(link)                
                link_seq_no += 1

                #from station to passenger virtual         
                for v_type in [1,3]:                    
                    if from_node_id_des in [0, param.num_station-1] and v_type!=1:
                        continue
                    if from_node_id_des not in network.stor_station_list and v_type!=1:
                        continue
                   
                    from_index_des=(from_node_id_des,t,run_dir,v_type)
                    from_node_seq_no=network.node_index_to_no_dict[from_index_des]
                    to_node_seq_no=network.node_index_to_no_dict[to_index_des]                    
                    link_cost=0
                    link_travel_time=link_cost
                    link_cap=param.max_pax_cap
                    index=(from_node_seq_no,to_node_seq_no)
                    network.link_index_to_no_dict[index]=link_seq_no 
                    link_type='vp'
                    link = Link(link_id, link_seq_no, from_node_id_des, to_node_id_des, from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,t)                    
                    link.start_time=t
                    link.end_time=-100
                    
                    network.link_list.append(link)                
                    network.node_list[from_node_seq_no].outgoing_link_list.append(link)
                    network.node_list[to_node_seq_no].incoming_link_list.append(link)                
                    link_seq_no += 1                


    #vitual arcs from passenger virtuals to passenger virtuals
    for w in demand.OD_list:
        run_dir=1 if w[0]<w[1] else 2
        from_node_id_ori=-w[0]-100
        to_node_id_des=-w[1]-100      
        
        from_index_ori=(from_node_id_ori,from_node_id_ori,from_node_id_ori,from_node_id_ori)
        to_index_des=(to_node_id_des,to_node_id_des,to_node_id_des,to_node_id_des)
        
        from_node_seq_no=network.node_index_to_no_dict[from_index_ori]
        # print(to_node_id_ori,t)
        to_node_seq_no=network.node_index_to_no_dict[to_index_des]        
        link_cost=param.vitual_pax_cost
        link_travel_time=link_cost
        link_cap=param.max_pax_cap
        index=(from_node_seq_no,to_node_seq_no)
        network.link_index_to_no_dict[index]=link_seq_no
        link_type='vv'
        link = Link(link_id, link_seq_no, w[0], w[1], from_node_seq_no, to_node_seq_no, link_cost, link_travel_time,link_cap,link_type,run_dir,-1)                    
        link.start_time=-100
        link.end_time=-100
        
        network.link_list.append(link)
        # print(from_node_seq_no,,"test...")
        network.node_list[from_node_seq_no].outgoing_link_list.append(link)
        network.node_list[to_node_seq_no].incoming_link_list.append(link)
        network.vir_arc_pax[w]=link_seq_no
        # print(w,link_seq_no)
        # print(network.vir_arc_pax[w])
        # input()
        link_seq_no += 1
    
    print(f"Number of links is: {link_seq_no}")
    network.link_size = link_seq_no
    
    
    # link_id=15985
    # print(network.link_list[link_id].from_node_seq_no,network.link_list[link_id].to_node_seq_no)
    # print(network.link_list[link_id].link_type,network.link_list[link_id].link_direction)
    # # print(network.link_no_dict_to_index[link_id])    
    # input()
    
    
    # node1_id= 654; node2_id=1038
    # print(network.link_index_to_no_dict[(node1_id,node2_id)])
    # print(network.node_list[node1_id].node_time,network.node_list[node2_id].node_time)
    # print(network.node_list[node1_id].node_id,network.node_list[node2_id].node_id)
    # print(network.node_no_dict_to_index[node1_id],network.node_no_dict_to_index[node2_id])
  
    # input()
    
    # v=network.node_list[node2_id]
    # for link in v.outgoing_link_list:
        # print(link.link_seq_no,link.link_type,link.from_node_seq_no,link.to_node_seq_no,link.from_node_id,link.to_node_id)
        # print(link.start_time,link.end_time)
    # input()
        
    # for sec in network.section_list:
        # s=sec.from_node_id
        # run_dir=sec.run_direction
        # for link_seq_no in (network.uncouple_arc[s,run_dir] + network.couple_arc[s,run_dir]):
            # link=network.link_list[link_seq_no]
            # if link.link_type not in ['ucd','cod']:
                # print(link.link_type,link_seq_no)
                # input()
    


def read_agents(input_dir, network):#读取问题
    # Read agent info#读取问题信息
    print("\nRead agent.csv")
    agent_num=0
    with open(input_dir + '/demand.csv', 'r', encoding='utf-8') as fp:
        reader = csv.DictReader(fp)
        for line in reader:
            time_threshold = _convert_str_to_int(line['t'])

            for w in demand.OD_list:
                index=str(w[0]*100+w[1])
                passenger_num = _convert_str_to_int(line[index])
                
                if param.earliest_time[w,w[0]]<=time_threshold<=param.latest_time[w,w[0]]:
                    demand.demand_dic[w,time_threshold]=passenger_num
                    agent_num+=passenger_num
                else:
                    demand.demand_dic[w,time_threshold]=0
                    
                # demand.demand_dic[w,time_threshold]=passenger_num
                # agent_num+=passenger_num
                
    
    for w in demand.OD_list:
        temp=0
        demand.demand_max[w]=0
        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
            temp_accum=0
            temp+=demand.demand_dic[w,t]
            for tp in range(param.earliest_time[w,w[0]],t+1):
                temp_accum+=demand.demand_dic[w,tp]
            demand.demand_accum[w,t]=temp_accum
            
            num_max=0
            for tp in range(t,min(t+10,param.latest_time[w,w[0]])):
                num_max+=demand.demand_dic[w,tp]
            if num_max>demand.demand_max[w]:
                demand.demand_max[w]=num_max
        
        demand.demand_OD[w]=temp
        
        dir=1 if w[0]<w[1] else 2
        param.OD_dir[w]=dir
        
        # print(w,demand.demand_OD[w])
        # input()


    for s in network.turnback_station_list:
        for run_dir in [1,2]:
            step=-1 if run_dir==1 else 1
            end_s= -1 if run_dir==1 else param.num_station
            start_s=None
            for sp in range(s+step,end_s,step):
                if sp in network.turnback_station_list:
                    start_s=sp
                    break
            
            temp_max=-1000
            # print(start_s,s,-step)
            # input()
            if start_s!=None:
                for sp in range(start_s,s,-step):
                    sec=network.sec_index_to_no_dict[run_dir,sp]
                    num=0
                    for w in sec.belong_OD_list:
                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                            num+=demand.demand_dic[w,t]
                    if temp_max<num:
                        temp_max=num
                
                for sp in range(start_s,s,-step): 
                    sec=network.sec_index_to_no_dict[run_dir,sp]
                    sec.max_train_unit=math.ceil(temp_max/param.single_cap)
                    # print(s,run_dir,sec.section_id,sec.max_train_unit)
                # input()    
        
    for sec in network.section_list:
        num=0
        for w in sec.belong_OD_list:
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]-sec.run_time-param.min_wait_time):
                num+=demand.demand_dic[w,t]        
        sec.demand_vol=num
        
            
        # print(sec.section_id,sec.demand_vol,sec.max_train_unit)
        # input()
        
        
        for t in range(param.max_time,-1,-1):
            num=0
            if param.train_early_time[sec.run_direction,sec.from_node_id]<=t<=param.train_latest_time[sec.run_direction,sec.from_node_id]:
                for w in sec.belong_OD_list:
                    step=1 if sec.run_direction==1 else -1
                    temp_time=0
                    for s in range(w[0],sec.from_node_id,step):
                        temp_time+=network.sec_index_to_no_dict[sec.run_direction,s].run_time
                    left_time=t-temp_time
                    right_time=param.latest_time[w,w[0]]
                    if left_time<=param.earliest_time[w,w[0]]:
                        left_time=right_time=0
                    for tp in range(left_time,right_time+1):
                        num+=demand.demand_dic[w,tp]
            sec.later_num_unit[t]=math.ceil(num/param.single_cap)
            # print(sec.section_id,sec.later_num_unit[t])
            # print(sec.section_id,t,num,sec.later_num_unit[t])
            # input()

    print(f"The number of agents is: {agent_num}")
        

def calculating_time_range():
    #calculating earliest and latest times for each station
    for w in demand.OD_list:        
        param.earliest_time[w,w[0]]=param.min_time
        param.latest_time[w,w[0]]=param.max_time

        dir=1 if w[0]<w[1] else 2
        #earliest time
        s=w[0]        
        end_s=-1 if dir==1 else param.num_station
        step=-1 if dir==1 else 1        
        for sp in range(s,end_s,step):
            if sp in network.turnback_station_list:
                time_early=0
                temp_t=0
                step_p=1 if dir==1 else -1
                stop_s=s+1 if dir==1 else s-1
                for spp in range(sp,stop_s,step_p):
                    time_early=temp_t
                    temp_t=time_early+network.sec_index_to_no_dict[dir,spp].run_time+param.min_wait_time
                    
                param.earliest_time[w,w[0]]=time_early
                break
        
        #latest time
        s=w[1]
        end_s=param.num_station if dir==1 else -1
        step=1 if dir==1 else -1        
        for sp in range(s,end_s,step):
            if sp in network.turnback_station_list:
                time_later=0
                if sp in [0,param.num_station-1]:
                    temp_t=param.max_time-1-param.transfer_time
                else:
                    temp_t=param.max_time-1-param.uncouple_to_storage_time
                
                step_p=-1 if dir==1 else 1
                # stop_s=w[0]-1 if dir==1 else w[0]+1
                for spp in range(sp,w[0],step_p):
                    temp_s=spp-1 if dir==1 else spp+1                    
                    time_later=temp_t-(network.sec_index_to_no_dict[dir,temp_s].run_time+param.min_wait_time)
                    temp_t=time_later
                    
                param.latest_time[w,w[0]]=time_later
                break
    
        # print(w,param.earliest_time[w,w[0]],param.latest_time[w,w[0]])
    # input()
    
    for w in demand.OD_list:
        run_dir=1 if w[0]<w[1] else 2
        step=1 if run_dir==1 else -1
        for s in range(w[0]+step,w[1]+step,step):
            sp=s-step
            # print(w,s)
            param.earliest_time[w,s]=param.earliest_time[w,sp]+network.sec_index_to_no_dict[run_dir,sp].run_time+param.min_wait_time
            param.latest_time[w,s]=param.latest_time[w,sp]+network.sec_index_to_no_dict[run_dir,sp].run_time+param.min_wait_time
            
        # for s in range(w[0],w[1]+step,step):
            # print(w,s)
            # print(param.earliest_time[w,s],param.latest_time[w,s])
            # input()
   
        
    # calculating time range for train
    for sec in network.section_list:
        from_n=sec.from_node_id
        to_n=sec.to_node_id        
        temp_min=100000
        temp_max=0
        for w in sec.belong_OD_list:
            if w[0]==from_n:
                if temp_min>param.earliest_time[w,w[0]]:
                    temp_min=param.earliest_time[w,w[0]]
                if temp_max<param.latest_time[w,w[0]]:
                    temp_max=param.latest_time[w,w[0]]
        
        # if sec.run_direction==1 and from_n==5:
            # print(sec.belong_OD_list)
            # input()
        
        
        param.train_early_time[sec.run_direction,from_n]=temp_min
        param.train_latest_time[sec.run_direction,from_n]=temp_max
        
        if sec.run_direction==1 and to_n==param.num_station-1:
            param.train_early_time[sec.run_direction,to_n]=param.train_early_time[sec.run_direction,to_n-1]+sec.run_time+param.min_wait_time
            param.train_latest_time[sec.run_direction,to_n]=param.train_latest_time[sec.run_direction,to_n-1]+sec.run_time+param.min_wait_time 
        elif sec.run_direction==2 and to_n==0:
            param.train_early_time[sec.run_direction,to_n]=param.train_early_time[sec.run_direction,to_n+1]+sec.run_time+param.min_wait_time
            param.train_latest_time[sec.run_direction,to_n]=param.train_latest_time[sec.run_direction,to_n+1]+sec.run_time+param.min_wait_time         
    
    # for dir in [1,2]:
        # for s in range(param.num_station):
            # print(dir,s,param.train_early_time[dir,s],param.train_latest_time[dir,s])
    # input()
    
    if param.rolling_flag==1: 
        for run_dir in [1,2]:
            if run_dir==1:
                sta_s=param.num_station-1
                end_s=0
                step=-1
            else:
                sta_s=0
                end_s=param.num_station-1
                step=1
            
            temp_t=0
            for s in range(sta_s,end_s+step,step):
                if s==sta_s:
                    temp_t=param.max_time-1-param.transfer_time
                else:
                    temp_t=temp_t-(network.sec_index_to_no_dict[run_dir,s].run_time+param.min_wait_time)
                
                param.train_latest_time[run_dir,s]=temp_t
                
                # print(run_dir,s,param.train_latest_time[run_dir,s])
                # input()
                
                for w in demand.OD_list:
                    r_dir=1 if w[0]<w[1] else 2
                    if r_dir==run_dir:
                        if w[0]<=s<=w[1] or w[1]<=s<=w[0]:
                            if param.latest_time[w,s] > param.train_latest_time[run_dir,s]:
                                param.latest_time[w,s] = param.train_latest_time[run_dir,s]
                        
                
    elif param.rolling_flag==2: #中间时段        
        #左边界
        for run_dir in [1,2]:
            if run_dir==1:
                sta_s=param.num_station-1
                end_s=0
                step=-1
            else:
                sta_s=0
                end_s=param.num_station-1
                step=1
            
            temp_t=0
            for s in range(sta_s,end_s+step,step):
                if s==sta_s:
                    temp_t=param.min_time-param.transfer_time
                else:
                    temp_t=temp_t-(network.sec_index_to_no_dict[run_dir,s].run_time+param.min_wait_time)
                
                param.train_early_time[run_dir,s]=temp_t
                
                # print(run_dir,s,param.train_early_time[run_dir,s])
                # input()
                
                for w in demand.OD_list:
                    r_dir=1 if w[0]<w[1] else 2
                    if r_dir==run_dir:
                        if w[0]<=s<=w[1] or w[1]<=s<=w[0]:
                            if param.earliest_time[w,s] < param.train_early_time[run_dir,s]:
                                param.earliest_time[w,s] = param.train_early_time[run_dir,s]
        
        #右边界
        for run_dir in [1,2]:
            if run_dir==1:
                sta_s=param.num_station-1
                end_s=0
                step=-1
            else:
                sta_s=0
                end_s=param.num_station-1
                step=1
            
            temp_t=0
            for s in range(sta_s,end_s+step,step):
                if s==sta_s:
                    temp_t=param.max_time-1-param.transfer_time
                else:
                    temp_t=temp_t-(network.sec_index_to_no_dict[run_dir,s].run_time+param.min_wait_time)
                
                param.train_latest_time[run_dir,s]=temp_t
                
                # print(run_dir,s,param.train_latest_time[run_dir,s])
                # input()
                
                for w in demand.OD_list:
                    r_dir=1 if w[0]<w[1] else 2
                    if r_dir==run_dir:
                        if w[0]<=s<=w[1] or w[1]<=s<=w[0]:
                            if param.latest_time[w,s] > param.train_latest_time[run_dir,s]:
                                param.latest_time[w,s] = param.train_latest_time[run_dir,s]
    
    
        # for w in demand.OD_list:
            # print(param.earliest_time[w,w[0]],param.latest_time[w,w[0]])
            # input()
    
    elif param.rolling_flag==3: #末尾时段
        #左边界
        for run_dir in [1,2]:
            if run_dir==1:
                sta_s=param.num_station-1
                end_s=0
                step=-1
            else:
                sta_s=0
                end_s=param.num_station-1
                step=1
            
            temp_t=0
            for s in range(sta_s,end_s+step,step):
                if s==sta_s:
                    temp_t=param.min_time-param.transfer_time
                else:
                    temp_t=temp_t-(network.sec_index_to_no_dict[run_dir,s].run_time+param.min_wait_time)
                
                param.train_early_time[run_dir,s]=temp_t
                
                # print(run_dir,s,param.train_early_time[run_dir,s])
                # input()
                
                for w in demand.OD_list:
                    r_dir=1 if w[0]<w[1] else 2
                    if r_dir==run_dir:
                        if w[0]<=s<=w[1] or w[1]<=s<=w[0]:
                            if param.earliest_time[w,s] < param.train_early_time[run_dir,s]:
                                param.earliest_time[w,s] = param.train_early_time[run_dir,s]
    
    

    # claclute OD runing time
    for s in range(param.num_station):
        for sp in range(param.num_station):            
            run_dir=1 if s<sp else 2
            step=1 if s<sp else -1
            temp_run=0
            for ss in range(s,sp,step):
                temp_run+=network.sec_index_to_no_dict[run_dir,ss].run_time
                
            network.OD_running_time[s,sp]=temp_run
            
            # print(s,sp,run_dir,temp_run)
            # input()
                
                


demand = Demand()
param = Param()
network = Network()
def read_network(input_dir):
    read_nodes(input_dir, network)
    read_links(input_dir, network)
    read_agents(input_dir, network)
    # output_demand("30_based_sec_demand")
    
    
    for w in demand.OD_list:
        run_dir=1 if w[0]<w[1] else 2
        network.OD_direction[w]=run_dir
        
        network.OD_station[w]=[]
        step =1 if w[0]<w[1] else -1
        for s in range(w[0],w[1]+step,step):
            network.OD_station[w].append(s)
        
        # print(w,network.OD_station[w])
        # print(network.OD_direction[w])
        # input()
            
    for s in range(param.num_station):
        if s in network.stor_station_list:
            network.max_start_unit[s]=network.station_storage[s]
        else:
            network.max_start_unit[s]=0            
    
    # num=0
    # num1=0
    # for w in demand.OD_list:
        # print(demand.demand_OD[w])
        # input()
        # for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):   
            # num+=param.weight_pax*param.wait_pax_cost*demand.demand_accum[w,t] 
        # num+=demand.demand_OD[w]
        # num1+=demand.demand_OD[w]
    # print(num,num1)
    # input()
    
    return demand,param,network


def output_demand(file_name):    
    output_dir='./VirtualCouple/Explarge/output'
        
    # with open(output_dir + "/result_"+file_name+".csv", "w", newline="") as fp:
        # writer = csv.writer(fp)
        # writer.writerow(['demand'])
        # for run_dir in [1,2]:
            # writer.writerow(['run_dir',run_dir])
            # for k in range(10):
                # temp=[]
                # s_time=k*30
                # e_time=(k+1)*30                
                # for s in range(param.num_station):                    
                    # num=0
                    # for w in demand.OD_list:
                        # w_dir=1 if w[0]<w[1] else 2
                        # if w_dir==run_dir and w[0]==s:
                            # for tp in range(s_time,e_time):
                                # num+=demand.demand_dic[w,tp]                        
                    # temp.append(num)
                # writer.writerow(temp) 
    # print("output successfull!")
    # input()
    
    #section passenger demand
    sec_demand={}
    for run_dir in [1,2]:
        for k in range(10):                        
            for s in range(param.num_station):
                sec_demand[run_dir,s,k]=0

    for w in demand.OD_list:
        run_dir=1 if w[0]<w[1] else 2
        for t in range(param.max_time):
            if run_dir==1:
                tp=t
                for s in range(w[0],w[1],1):
                    k=tp//30
                    if tp<param.max_time:
                        sec_demand[run_dir,s,k]+=demand.demand_dic[w,t]
                    tp+=network.sec_index_to_no_dict[run_dir,s].run_time
            elif run_dir==2:
                tp=t
                for s in range(w[0],w[1],-1):
                    k=tp//30
                    if tp<param.max_time:
                        sec_demand[run_dir,s,k]+=demand.demand_dic[w,t]
                    tp+=network.sec_index_to_no_dict[run_dir,s].run_time
    
    with open(output_dir + "/result_"+file_name+".csv", "w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(['demand'])
        for run_dir in [1,2]:
            writer.writerow(['run_dir',run_dir])
            for k in range(10):
                temp=[]                       
                for s in range(param.num_station):  
                    temp.append(sec_demand[run_dir,s,k])
                writer.writerow(temp) 
    print("output successfull!")
    input()
    
    # with open(output_dir + "/result_"+file_name+".csv", "w", newline="") as fp:
        # writer = csv.writer(fp)        
        
        # temp=['t']
        # for s in range(param.num_station):
            # for sp in range(s+1,param.num_station):
                # temp.append(s*100+sp)
                
        # for s in range(param.num_station-1,-1,-1):
            # for sp in range(s-1,-1,-1):
                # temp.append(s*100+sp)
                
        # writer.writerow(temp)        
    
        
        # for t in range(param.max_time):
            # temp=[t]
            # for s in range(param.num_station):
                # for sp in range(s+1,param.num_station):
                    # temp.append(demand.demand_dic[(s,sp),t])
                    
            # for s in range(param.num_station-1,-1,-1):
                # for sp in range(s-1,-1,-1):
                    # temp.append(demand.demand_dic[(s,sp),t])
    
            # writer.writerow(temp) 
    # print("output successfull!")
    # input()
    
    # with open(output_dir + "/result_"+file_name+"_up"+".csv", "w", newline="") as fp:
        # writer = csv.writer(fp)        
        
        # #up direction
        # temp=['t']
        # for s in range(param.num_station):
            # for sp in range(s+1,param.num_station):
                # temp.append("'"+str(s)+'-'+str(sp))          
                
        # writer.writerow(temp)      
    
        # for i in range(100):
            # temp=[i]
            # for s in range(param.num_station):
                # for sp in range(s+1,param.num_station):
                    # num=0
                    # for t in range(i*3,(i+1)*3):
                        # num += demand.demand_dic[(s,sp),t] 
                    # temp.append(num)
            # writer.writerow(temp)   
    

    # with open(output_dir + "/result_"+file_name+"_down"+".csv", "w", newline="") as fp:
        # writer = csv.writer(fp)        
        
        # #down direction
        # temp=['t']                
        # for s in range(param.num_station-1,-1,-1):
            # for sp in range(s-1,-1,-1):
                # temp.append("'"+str(s)+'-'+str(sp))
                
        # writer.writerow(temp)      
    
        # for i in range(100):
            # temp=[i]
            # for s in range(param.num_station-1,-1,-1):
                # for sp in range(s-1,-1,-1):
                    # num=0
                    # for t in range(i*3,(i+1)*3):
                        # num += demand.demand_dic[(s,sp),t] 
                    # temp.append(num)
            # writer.writerow(temp)   
            
    # print("output successfull!")
    # input()