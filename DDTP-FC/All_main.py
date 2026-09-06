import csv#读写调查CSV文件
import os#用于访问操作系统功能的模块， os模块提供了其他操作系统接口，可以实现跨平台访问
import gurobipy as gb 
import math
import random

from collections import defaultdict
from ConstructNetwork import read_network
from utils import _convert_str_to_int
import copy
# from Callback import mycallback


class WarmStartInitialSol:
    def __init__(self):  
        self.__first_origin_model = gb.Model("first_origin_model")
        self.second_origin_model = gb.Model("second_origin_model")    
        self.z_var={}
        self.feasible_time  = {}
        
        for run_dir in [1,2]:
            for s in range(param.num_station):
                self.feasible_time[run_dir,s]=[]
        
        
        self.feasible_link_for_bestSol=[]
        self.max_const={}
        self.remain_pax={}
        self.y_vir={} 
        for w in demand.OD_list:
            self.remain_pax[w]=0
        
        self.__predetermine_range()
          
        self.z_v={}
        self.b_v={}   

        self.ini_b_v={}
        self.ini_z_v={}     
        
        self.estimate_lower_bound=0
        self.min_virt_pax=0
        
        self.lower_bound_period={}
        self.max_period={}
        
        self.sec_estimate_lower_bound={}
        for sec in network.section_list:
            self.sec_estimate_lower_bound[sec.section_id]=0      

        self.const_dic={}    
        
        self.lower_bound_OD={}
        self.lower_bound_OD_waittime={}
        
        self.last_time={}
        self.last_link=[]
        if param.rolling_flag!=1 and param.rolling_flag!=0:
            self.__input_prePeriod_solution()
        if param.rolling_flag!=3 and param.rolling_flag!=0:
            for run_dir in [1,2]:
                for s in range(param.num_station):
                    network.end_unit[run_dir,s]=0
        
        
        self.__input_initial_solution()
        
    def __predetermine_range(self):
        step=1
        s=param.num_station-1
        temp={}
        temp[s]=param.train_latest_time[1,s]
        for sp in range(s-1,-1,-1):
            sec=network.sec_index_to_no_dict[1,sp]
            temp[sp]=temp[sp+1]-sec.run_time
        for sp in range(s+1):
            for t in range(temp[sp],param.train_early_time[1,sp]-1,-step):
                if t not in self.feasible_time[1,sp]:
                    self.feasible_time[1,sp].append(t)
            for t in range(temp[sp],param.train_latest_time[1,sp]+1,+step):
                if t not in self.feasible_time[1,sp]:
                    self.feasible_time[1,sp].append(t)
            
            for t in range(param.train_latest_time[1,sp],param.train_latest_time[1,sp]+1):
                if t not in self.feasible_time[1,sp]:
                    self.feasible_time[1,sp].append(t)
            
        # print(self.feasible_time[1,1])
        # print(param.train_early_time[1,5],param.train_latest_time[1,5])
        # input()
        
        s=0
        temp={}
        temp[s]=param.train_latest_time[2,s]
        for sp in range(s+1,param.num_station):
            sec=network.sec_index_to_no_dict[2,sp]
            temp[sp]=temp[sp-1]-sec.run_time
        for sp in range(s,param.num_station):
            # print(s,sp)
            for t in range(temp[sp],param.train_early_time[2,sp]-1,-step):
                if t not in self.feasible_time[2,sp]:
                    self.feasible_time[2,sp].append(t)
            for t in range(temp[sp],param.train_latest_time[2,sp]+1,+step): 
                self.feasible_time[2,sp].append(t)
                
            if param.train_latest_time[2,sp] not in self.feasible_time[2,sp]:
                self.feasible_time[2,sp].append(t)        

        # for s in range(param.num_station):
            # # print(self.feasible_time[1,s])
            # # print(1,s,param.train_early_time[1,s],param.train_latest_time[1,s])
            # print(2,s,param.train_early_time[2,s],param.train_latest_time[2,s])
            # input()
         
       

        # for sec in network.section_list:
            # from_n=sec.from_node_id
            # to_n=sec.to_node_id
            # run_dir=sec.run_direction            
            # flag=0
            # step=1 if run_dir==1 else -1
            # # print(param.train_early_time[run_dir,from_n]-1)
            # # print(from_n,run_dir)
            # # input()
            # for t in range(param.train_latest_time[run_dir,from_n],param.train_early_time[run_dir,from_n]-1,-1):
                # if flag%(9)==0:
                    # from_index=(from_n,t,run_dir,1)
                    # from_node_seq_no=network.node_index_to_no_dict[from_index]
                    # tp=t+sec.run_time
                    # for v_type in [1,2,3]:
                        # to_index=(from_n+step,tp,run_dir,v_type)
                        # if to_index in network.node_index_to_no_dict.keys():
                            # to_node_seq_no=network.node_index_to_no_dict[to_index]
                            # index=(from_node_seq_no,to_node_seq_no)
                            # if index in network.link_index_to_no_dict.keys():
                                # link_seq_no=network.link_index_to_no_dict[index] 
                                # # self.feasible_link_for_bestSol.append(link_seq_no)
                                # # print(link_seq_no)
                                # # print(from_n,t,run_dir,flag)
                                # # input()
                # flag+=1
        # print("length of self.feasible_link_for_bestSol:",len(self.feasible_link_for_bestSol))
        # input()

    def __train_lower_bound_minutes(self):        
        val_lb=0
        for sec in network.section_list:
            from_n=sec.from_node_id
            to_n=sec.to_node_id
            run_dir=sec.run_direction
            
            unit_time=60
            max_iter=int((param.train_latest_time[run_dir,from_n]-param.train_early_time[run_dir,from_n])/unit_time)
            self.max_period[sec.section_id]=max_iter
            # print(max_iter,param.train_latest_time[run_dir,from_n]-param.train_early_time[run_dir,from_n])
            # input()
            for pt in range(max_iter):
                if pt==max_iter-1:
                    sta_time=pt*unit_time
                    end_time=param.train_latest_time[run_dir,from_n]+1
                else:
                    sta_time=pt*unit_time
                    end_time=(pt+1)*unit_time
                
                curr_arrive={}
                for w in sec.belong_OD_list:                
                    if w[0]==from_n:
                        for t in range(sta_time,end_time):
                            # accum_arrive[t]=0
                            if t in curr_arrive.keys():
                                curr_arrive[t]+=demand.demand_dic[w,t]
                            else:
                                curr_arrive[t]=demand.demand_dic[w,t]
                            # for tp in range(param.train_early_time[run_dir,from_n],t+1):
                                # accum_arrive[t]+=demand.demand_dic[w,tp]
                
                sec_model = gb.Model("sec_model")
                z=gb.tupledict()
                w_time=gb.tupledict()
                re_main=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='re_main')
                for t in range(sta_time,end_time):
                    for l in param.level_comosition:
                        z[t,l]=sec_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(t,l))

                    w_time[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='w_time[%d]'%(t))
                  
                # sec_model.addConstr(gb.quicksum(z[t,l]*l for t in range(sta_time,end_time)
                                                       # for l in param.level_comosition)
                                                       # >= sec.max_train_unit,name="MC7")             
            
                sec_model.addConstr(gb.quicksum(z[t,l] for t in range(sta_time,end_time)
                                                   for l in param.level_comosition)
                                                   <= 30,name="MC71")
                
                
                for t in range(sta_time,end_time):                
                    temp_safe_node=[]
                    for tp in range(t,t+param.safe_interval):                    
                        tpp=tp+sec.run_time
                        if tpp<end_time+sec.run_time:
                            temp_safe_node.append(tp)
                    
                    temp_safe_node_max=[]
                    if sta_time<=t<end_time-param.max_interval:
                        for tp in range(t,t+param.max_interval):                    
                            tpp=tp+sec.run_time
                            if tpp<end_time+sec.run_time:
                                temp_safe_node_max.append(tp)
                    
                    if len(temp_safe_node)>0:
                        sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node))
                                <= 1,name="MC2[%d]"%(t))             
                

                    if len(temp_safe_node_max)>0:
                        sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node_max))
                                >= 1,name="MC21[%d]"%(t))
                    
                    if t>sta_time:     
                        sec_model.addConstr(w_time[t] >=
                                w_time[t-1]+curr_arrive[t]-param.single_cap*gb.quicksum(z[t,l]*l for l in param.level_comosition)
                        ,name="MC91[%d]"%(t))
                    else:
                        sec_model.addConstr(w_time[t] >=
                                curr_arrive[t]-param.single_cap*gb.quicksum(z[t,l]*l for l in param.level_comosition)
                        ,name="MC91[%d]"%(t))

                if pt==max_iter-1:
                    sec_model.addConstr(re_main >=
                            w_time[end_time-1]*param.vitual_pax_cost
                    ,name="MC10")
                else:
                    sec_model.addConstr(re_main >=
                            w_time[end_time-1]#*param.vitual_pax_cost
                    ,name="MC10")
                              
                sec_model.setObjective(param.weight_pax*gb.quicksum(w_time[t]*param.wait_pax_cost
                for t in range(sta_time,end_time))
                +sec.sec_dis*param.weight_train*gb.quicksum(z[t,l]*param.cost_composition[l]
                    for t in range(sta_time,end_time)
                        for l in param.level_comosition)
                        +param.weight_pax*re_main,gb.GRB.MINIMIZE)
            
                sec_model.update()
                sec_model.Params.outputflag=0
                # sec_model.Params.MIPGap=0.01
                # sec_model.Params.TimeLimit=15
                sec_model.optimize()

                self.lower_bound_period[sec.section_id,pt]=sec_model.objVal
                
                # print(sec.section_id,pt,sec_model.objVal)
                # input()
                
                val_lb+=sec_model.objVal
        
        print("estimate_lower_bound:",val_lb)
        input()

    def __train_lower_bound_new(self):        
        for sec in network.section_list:
            from_n=sec.from_node_id
            to_n=sec.to_node_id
            run_dir=sec.run_direction
            
            curr_arrive={}
            other_arrive={}
            num_t1=0
            num_t2=0
            for w in sec.belong_OD_list:                
                if w[0]==from_n:
                    for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                        # accum_arrive[t]=0
                        if t in curr_arrive.keys():
                            curr_arrive[t]+=demand.demand_dic[w,t]
                            num_t1+=demand.demand_dic[w,t]
                        else:
                            curr_arrive[t]=demand.demand_dic[w,t]
                            num_t1+=demand.demand_dic[w,t]
                        # for tp in range(param.train_early_time[run_dir,from_n],t+1):
                            # accum_arrive[t]+=demand.demand_dic[w,tp]
                else:
                    w_run_dir=1 if w[0]<w[1] else 2
                    step =1 if w_run_dir==1 else -1
                    run_time=0
                    for s in range(w[0],from_n,step):
                        sec_p=network.sec_index_to_no_dict[w_run_dir,s]
                        run_time+=sec_p.run_time
                        
                    for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                        if param.earliest_time[w,from_n]<=t+run_time<=param.latest_time[w,from_n]:                        
                            if t+run_time in other_arrive.keys():
                                other_arrive[t+run_time]+=demand.demand_dic[w,t+run_time]
                                num_t2+=demand.demand_dic[w,t+run_time]
                            else:
                                other_arrive[t+run_time]=demand.demand_dic[w,t+run_time]
                                num_t2+=demand.demand_dic[w,t+run_time]
            

            for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1):
                if t not in curr_arrive.keys():
                    curr_arrive[t]=0
                if t not in other_arrive.keys():
                    other_arrive[t]=0
                
            sec_model = gb.Model("sec_model")
            z=gb.tupledict()
            w_time=gb.tupledict()
            other_w_time=gb.tupledict()
            
            b_pax=gb.tupledict()
            other_b_pax=gb.tupledict()
            
            re_main=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='re_main')
            
            for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1):
                for l in param.level_comosition:
                    z[t,l]=sec_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(t,l))

                w_time[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='w_time[%d]'%(t))
                other_w_time[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='o_w_time[%d]'%(t))
                
                b_pax[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='b_pax[%d]'%(t))
                other_b_pax[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='other_b_pax[%d]'%(t))
                
                
            sec_model.addConstr(gb.quicksum(z[t,l]*l for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1)
                                                   for l in param.level_comosition)
                                                   >= sec.max_train_unit,name="MC7")             
        
            sec_model.addConstr(gb.quicksum(z[t,l] for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1)
                                                   for l in param.level_comosition)
                                                   <= 20,name="MC71")  
            
            for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):
                    tpp=tp+sec.run_time
                    if tpp<param.train_latest_time[run_dir,to_n]+1:
                        temp_safe_node.append(tp)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_n]<=t<param.train_latest_time[run_dir,from_n]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        tpp=tp+sec.run_time
                        if tpp<param.train_latest_time[run_dir,to_n]+1:
                            temp_safe_node_max.append(tp)
                
                if len(temp_safe_node)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node))
                            <= 1,name="MC2[%d]"%(t))

                if len(temp_safe_node_max)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node_max))
                            >= 1,name="MC21[%d]"%(t))
                
                if t>param.train_early_time[run_dir,from_n]:     
                    sec_model.addConstr(w_time[t] ==
                            w_time[t-1]+curr_arrive[t]-b_pax[t]
                    ,name="MC91[%d]"%(t))

                if t>param.train_early_time[run_dir,from_n]:     
                    sec_model.addConstr(other_w_time[t] ==
                            other_w_time[t-1]+other_arrive[t]-other_b_pax[t]
                    ,name="MC92[%d]"%(t))
                    
                sec_model.addConstr(other_b_pax[t]+b_pax[t]<=param.single_cap*gb.quicksum(l*z[t,l] for l in param.level_comosition)
                ,name="MC93[%d]"%(t))
                
                sec_model.addConstr((gb.quicksum(z[t,l] for l in param.level_comosition))
                            <= 1) 

            sec_model.addConstr(re_main ==
                    (w_time[param.train_latest_time[run_dir,from_n]]+other_w_time[param.train_latest_time[run_dir,from_n]])*param.vitual_pax_cost
            ,name="MC10")
            
            # sec_model.addConstr(gb.quicksum(z[t,l]
                # for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1)
                    # for l in param.level_comosition)
                    # >=135
            # ,name="MC11")
            
            sec_model.setObjective(gb.quicksum(w_time[t]
            for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1))
            +param.weight_train*sec.sec_dis*gb.quicksum(z[t,l]*param.cost_composition[l]
                for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1)
                    for l in param.level_comosition)
                    +re_main,gb.GRB.MINIMIZE)
        
            sec_model.update()
            sec_model.Params.outputflag=0
            sec_model.Params.MIPGap=0.01
            sec_model.Params.TimeLimit=600
            sec_model.optimize()
            
            train_cost=0
            pax_wait=0
            num=0
            for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1):
                for l in param.level_comosition:
                    num+=z[t,l].x
                    train_cost+=sec.sec_dis*z[t,l].x*param.cost_composition[l]
                pax_wait+=w_time[t].x
            
            
            # input()
            self.estimate_lower_bound += param.weight_train*train_cost
            self.estimate_lower_bound += param.weight_pax*(pax_wait+re_main.x)

            self.sec_estimate_lower_bound[sec.section_id]=param.weight_pax*(pax_wait+re_main.x)+param.weight_train*train_cost

            print("sec:",sec.section_id,self.sec_estimate_lower_bound[sec.section_id])
            print("train NUM:",num,sec_model.objVal)
            print(num_t1,num_t2)
            # input()

        print("estimate_lower_bound:",self.estimate_lower_bound)
        # input()

    def __train_lower_bound_OD(self):    
        for w in demand.OD_list:
        # for w in param.key_OD_list:
            print(w)
            s=w[0]
            sp=w[1]
            run_dir=1 if s<sp else 2
            step=1 if run_dir==1 else -1
            
            tt_sec_dis=0
            for sb in range(s,sp,step):
                sec=network.sec_index_to_no_dict[run_dir,sb]
                tt_sec_dis+=sec.sec_dis
            
            curr_arrive={} 
            num_t1=0
            temp_OD=[]
            for wp in demand.OD_list:
                p_run_dir=1 if wp[0]<wp[1] else 2
                # print(wp,p_run_dir)
                flag_ture=False
                if wp[0]==w[0] and wp[1]>=w[1] and p_run_dir==1 and p_run_dir==run_dir:
                    flag_ture=True
                    temp_OD.append(wp)
                elif wp[0]==w[0] and wp[1]<=w[1] and p_run_dir==2 and p_run_dir==run_dir:
                    flag_ture=True
                    temp_OD.append(wp)
                    
                if flag_ture==True:                   
                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1):
                        if t in curr_arrive.keys():
                            curr_arrive[t]+=demand.demand_dic[wp,t]
                            num_t1+=demand.demand_dic[wp,t]
                        else:
                            curr_arrive[t]=demand.demand_dic[wp,t]
                            num_t1+=demand.demand_dic[wp,t]
                    
            # print(w,"***")
            # print(temp_OD)
            # input()
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                if t not in curr_arrive.keys():
                    curr_arrive[t]=0
            
            sec_model = gb.Model("sec_model")
            z=gb.tupledict()
            w_time=gb.tupledict()
            
            b_pax=gb.tupledict()
            
            re_main=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='re_main')
            
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                for l in param.level_comosition:
                    z[t,l]=sec_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(t,l))

                w_time[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='w_time[%d]'%(t))
               
                b_pax[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='b_pax[%d]'%(t))
              
                
            # # sec_model.addConstr(gb.quicksum(z[t,l]*l for t in range(param.train_early_time[run_dir,s],param.train_latest_time[run_dir,s]+1)
                                                   # # for l in param.level_comosition)
                                                   # # >= sec.max_train_unit,name="MC7")             
            
            # sec_model.addConstr(gb.quicksum(z[t,l] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                                                   # for l in param.level_comosition)
                                                   # <= 30,name="MC71")
            
            if run_dir==2:
                sec_model.addConstr(gb.quicksum(z[t,l] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                                                       for l in param.level_comosition)
                                                       <= 30,name="MC72")
                sec_model.addConstr(gb.quicksum(z[t,l] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                                                       for l in param.level_comosition)
                                                       >= 20,name="MC73")
            if run_dir==1:
                sec_model.addConstr(gb.quicksum(z[t,l] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                                                       for l in param.level_comosition)
                                                       <= 10,name="MC73")
                sec_model.addConstr(gb.quicksum(z[t,l] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                                                       for l in param.level_comosition)
                                                       >= 5,name="MC74")
            
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):
                    tpp=tp+tt_sec_dis
                    if tpp<param.latest_time[w,sp]+1 and tp <=param.latest_time[w,s]:
                        temp_safe_node.append(tp)
                
                temp_safe_node_max=[]
                if param.earliest_time[w,s]<=t<param.latest_time[w,s]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        tpp=tp+tt_sec_dis
                        if tpp<param.latest_time[w,sp]+1  and tp <=param.latest_time[w,s]:
                            temp_safe_node_max.append(tp)
                
                if len(temp_safe_node)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node))
                            <= 1,name="MC2[%d]"%(t))             
            

                if len(temp_safe_node_max)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node_max))
                            >= 1,name="MC21[%d]"%(t))
                
                if t>param.earliest_time[w,s]:     
                    sec_model.addConstr(w_time[t] ==
                            w_time[t-1]+curr_arrive[t]-b_pax[t]
                    ,name="MC91[%d]"%(t))
                elif t==param.earliest_time[w,s]:
                    sec_model.addConstr(w_time[t] ==
                            curr_arrive[t]-b_pax[t]
                    ,name="MC91[%d]"%(t))
                
                sec_model.addConstr(b_pax[t]<=1*param.single_cap*gb.quicksum(l*z[t,l] for l in param.level_comosition)
                ,name="MC93[%d]"%(t))
                
                sec_model.addConstr((gb.quicksum(z[t,l] for l in param.level_comosition))
                            <= 1)

            sec_model.addConstr(re_main ==
                    (w_time[param.latest_time[w,s]])*param.vitual_pax_cost
            ,name="MC10")
        
            sec_model.setObjective(gb.quicksum(w_time[t]
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
            +param.weight_train*tt_sec_dis*gb.quicksum(z[t,l]*param.cost_composition[l]
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                    for l in param.level_comosition)
                    +re_main,gb.GRB.MINIMIZE)
        
            sec_model.update()
            sec_model.Params.outputflag=0
            sec_model.Params.MIPGap=0.01
            sec_model.Params.TimeLimit=600
            sec_model.optimize()
            
            self.lower_bound_OD[w]=sec_model.objVal
            
            
            # num_w=0
            # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                # num_w += w_time[t].x
                
            # num_w += re_main.x    
            # self.lower_bound_OD_waittime[w]=num_w
            
            # num=0
            # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                # for l in param.level_comosition:
                    # num+=z[t,l].x
            print(w,self.lower_bound_OD[w])
            # print(num)
            # input()
            # print(w,val_obj)
            # print(sec_model.status,"***")
            # # input()
            # print(sec_model.objVal)
            # print(num_t1)
            # input()

    
    def __train_lower_bound_OD_WT(self):    
        for w in demand.OD_list:
        # for w in param.key_OD_list:
            print(w)
            s=w[0]
            sp=w[1]
            run_dir=1 if s<sp else 2
            step=1 if run_dir==1 else -1
            
            tt_sec_dis=0
            for sb in range(s,sp,step):
                sec=network.sec_index_to_no_dict[run_dir,sb]
                tt_sec_dis+=sec.sec_dis
            
            curr_arrive={} 
            num_t1=0
            temp_OD=[]
            for wp in demand.OD_list:
                p_run_dir=1 if wp[0]<wp[1] else 2
                # print(wp,p_run_dir)
                flag_ture=False
                if wp[0]==w[0] and wp[1]>=w[1] and p_run_dir==1 and p_run_dir==run_dir:
                    flag_ture=True
                    temp_OD.append(wp)
                elif wp[0]==w[0] and wp[1]<=w[1] and p_run_dir==2 and p_run_dir==run_dir:
                    flag_ture=True
                    temp_OD.append(wp)
                    
                if flag_ture==True:                   
                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1):
                        if t in curr_arrive.keys():
                            curr_arrive[t]+=demand.demand_dic[wp,t]
                            num_t1+=demand.demand_dic[wp,t]
                        else:
                            curr_arrive[t]=demand.demand_dic[wp,t]
                            num_t1+=demand.demand_dic[wp,t]
                    
            # print(w,"***")
            # print(temp_OD)
            # input()
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                if t not in curr_arrive.keys():
                    curr_arrive[t]=0
            
            sec_model = gb.Model("sec_model")
            z=gb.tupledict()
            w_time=gb.tupledict()
            
            b_pax=gb.tupledict()
            
            re_main=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='re_main')
            
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                for l in param.level_comosition:
                    z[t,l]=sec_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(t,l))

                w_time[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='w_time[%d]'%(t))
               
                b_pax[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='b_pax[%d]'%(t))
            
            
            # # sec_model.addConstr(gb.quicksum(z[t,l]*l for t in range(param.train_early_time[run_dir,s],param.train_latest_time[run_dir,s]+1)
                                                   # # for l in param.level_comosition)
                                                   # # >= sec.max_train_unit,name="MC7")             
            
            # sec_model.addConstr(gb.quicksum(z[t,l] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                                                   # for l in param.level_comosition)
                                                   # <= 30,name="MC71")
            
            if run_dir==2:
                sec_model.addConstr(gb.quicksum(z[t,l] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                                                       for l in param.level_comosition)
                                                       == 30,name="MC72")
            if run_dir==1:
                sec_model.addConstr(gb.quicksum(z[t,l] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                                                       for l in param.level_comosition)
                                                       == 10,name="MC72")
            
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):
                    tpp=tp+tt_sec_dis
                    if tpp<param.latest_time[w,sp]+1 and tp <=param.latest_time[w,s]:
                        temp_safe_node.append(tp)
                
                temp_safe_node_max=[]
                if param.earliest_time[w,s]<=t<param.latest_time[w,s]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        tpp=tp+tt_sec_dis
                        if tpp<param.latest_time[w,sp]+1  and tp <=param.latest_time[w,s]:
                            temp_safe_node_max.append(tp)
                
                if len(temp_safe_node)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node))
                            <= 1,name="MC2[%d]"%(t))             
            

                if len(temp_safe_node_max)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node_max))
                            >= 1,name="MC21[%d]"%(t))
                
                if t>param.earliest_time[w,s]:     
                    sec_model.addConstr(w_time[t] ==
                            w_time[t-1]+curr_arrive[t]-b_pax[t]
                    ,name="MC91[%d]"%(t))
                elif t==param.earliest_time[w,s]:
                    sec_model.addConstr(w_time[t] ==
                            curr_arrive[t]-b_pax[t]
                    ,name="MC91[%d]"%(t))
                
                sec_model.addConstr(b_pax[t]<=1*param.single_cap*gb.quicksum(l*z[t,l] for l in param.level_comosition)
                ,name="MC93[%d]"%(t))
                
                sec_model.addConstr((gb.quicksum(z[t,l] for l in param.level_comosition))
                            <= 1)

            sec_model.addConstr(re_main ==
                    (w_time[param.latest_time[w,s]])*param.vitual_pax_cost
            ,name="MC10")
        
            sec_model.setObjective(gb.quicksum(w_time[t]
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
            +param.weight_train*tt_sec_dis*gb.quicksum(z[t,l]*param.cost_composition[l]
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)
                    for l in param.level_comosition)
                    +re_main,gb.GRB.MINIMIZE)
        
            sec_model.update()
            sec_model.Params.outputflag=0
            sec_model.Params.MIPGap=0.01
            sec_model.Params.TimeLimit=600
            sec_model.optimize()
            
            # self.lower_bound_OD[w]=sec_model.objVal
            
            # if w==(12,0):
                # sec_model.computeIIS()
                # sec_model.write("xxx33.ilp")
                # print("model,xxx333")
                # input()
            
            num_w=0
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                num_w += w_time[t].x
              
                
            num_w += re_main.x    
            self.lower_bound_OD_waittime[w]=num_w
            
            # num=0
            # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                # for l in param.level_comosition:
                    # num+=z[t,l].x
            print(w,self.lower_bound_OD_waittime[w])
            # print(num)
            # input()
            # print(w,val_obj)
            # print(sec_model.status,"***")
            # # input()
            # print(sec_model.objVal)
            # print(num_t1)
            # input()
    
    def __train_lower_bound(self):        
        for sec in network.section_list:
            from_n=sec.from_node_id
            to_n=sec.to_node_id
            run_dir=sec.run_direction
            
            curr_arrive={}
            for w in sec.belong_OD_list:                
                if w[0]==from_n:
                    for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1):
                        # accum_arrive[t]=0
                        if t in curr_arrive.keys():
                            curr_arrive[t]+=demand.demand_dic[w,t]
                        else:
                            curr_arrive[t]=demand.demand_dic[w,t]
                        # for tp in range(param.train_early_time[run_dir,from_n],t+1):
                            # accum_arrive[t]+=demand.demand_dic[w,tp]
            
            sec_model = gb.Model("sec_model")
            z=gb.tupledict()
            w_time=gb.tupledict()
            re_main=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='re_main')
            for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1):
                for l in param.level_comosition:
                    z[t,l]=sec_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(t,l))

                w_time[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='w_time[%d]'%(t))
              
            sec_model.addConstr(gb.quicksum(z[t,l]*l for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1)
                                                   for l in param.level_comosition)
                                                   >= sec.max_train_unit,name="MC7")             
        
            
            for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    tpp=tp+sec.run_time
                    if tpp<param.train_latest_time[run_dir,to_n]+1:
                        temp_safe_node.append(tp)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_n]<=t<param.train_latest_time[run_dir,from_n]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        tpp=tp+sec.run_time
                        if tpp<param.train_latest_time[run_dir,to_n]+1:
                            temp_safe_node_max.append(tp)
                
                if len(temp_safe_node)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node))
                            <= 1,name="MC2[%d]"%(t))             
            

                if len(temp_safe_node_max)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node_max))
                            >= 1,name="MC21[%d]"%(t))
                
                if t>param.train_early_time[run_dir,from_n]:     
                    sec_model.addConstr(w_time[t] >=
                            w_time[t-1]+curr_arrive[t]-1*param.single_cap*gb.quicksum(z[t,l]*l for l in param.level_comosition)
                    ,name="MC91[%d]"%(t))

            sec_model.addConstr(re_main >=
                    w_time[param.train_latest_time[run_dir,from_n]]*param.vitual_pax_cost
            ,name="MC10")
            
            # sec_model.addConstr(gb.quicksum(z[t,l]
                # for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1)
                    # for l in param.level_comosition)
                    # >=135
            # ,name="MC11")
            
            sec_model.setObjective(gb.quicksum(w_time[t]+curr_arrive[t]
            for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1))
            +param.weight_train*gb.quicksum(z[t,l]*param.cost_composition[l]
                for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1)
                    for l in param.level_comosition)
                    +re_main,gb.GRB.MINIMIZE)
        
            sec_model.update()
            sec_model.Params.outputflag=0
            sec_model.Params.MIPGap=0.01
            # sec_model.Params.TimeLimit=15
            sec_model.optimize()
            
            train_cost=0
            pax_wait=0
            for t in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1):
                for l in param.level_comosition:
                    train_cost+=sec.sec_dis*z[t,l].x*param.cost_composition[l]
                pax_wait+=w_time[t].x
            
            print("sec:",sec.section_id,train_cost,param.weight_train*train_cost,pax_wait,re_main.x)
            input()
            self.estimate_lower_bound += param.weight_train*train_cost
            self.estimate_lower_bound += param.weight_pax*(pax_wait+re_main.x)

            self.sec_estimate_lower_bound[sec.section_id]=param.weight_pax*(pax_wait+re_main.x)+param.weight_train*train_cost

        print("estimate_lower_bound:",self.estimate_lower_bound)
        # input()
    
    def __ite_first_origin_pro(self):
        obj_train=self.__first_origin_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_train')
        obj_pax=self.__first_origin_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_pax')
        x=gb.tupledict()
        y=gb.tupledict()
        for a in network.link_list:
            #train-related varibles
            st=a.start_time
            if a.link_type not in ['vp','vv']:
                x[a.link_seq_no]=self.__first_origin_model.addVar(lb=0,ub=a.link_cap,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
                if a.link_type in ['ur','dr']:        
                    for l in param.level_comosition:
                        # z[a.link_seq_no,l]=self.__first_origin_model.addVar(lb=0,ub=1,vtype=gb.GRB.CONTINUOUS,name='z[%d,%d]'%(a.link_seq_no,l))                    
                        # if a.link_seq_no==4591:
                            # print(st)
                            # print(self.feasible_time[a.link_direction,a.from_node_id])
                            # input()
                            
                        if st in self.feasible_time[a.link_direction,a.from_node_id]:
                            self.z_var[a.link_seq_no,l]=self.__first_origin_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        else:
                            self.z_var[a.link_seq_no,l]=self.__first_origin_model.addVar(lb=0,ub=0,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                if a.link_type in ['cod','ucd']:
                    for l in param.level_comosition:
                        self.z_var[a.link_seq_no,l]=self.__first_origin_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))                    
            
            #pax-related varibles
            if a.link_type not in ['vt','tud','tdu','idl','ucr']:
                for w in demand.OD_list:
                    run_dir=1 if w[0]<w[1] else 2 
                    if a.link_type=='vv' and a.from_node_id==w[0] and a.to_node_id==w[1]:
                        y[w,a.link_seq_no]=self.__first_origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                        self.y_vir[w]=y[w,a.link_seq_no]
                    elif a.link_type=='vp' and (a.from_node_id==w[1] or a.to_node_id==w[0]) and a.link_direction==run_dir:
                        y[w,a.link_seq_no]=self.__first_origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                    elif a.link_type not in ['vv','vp'] and a.link_direction==run_dir:
                        if (w[0]<=a.from_node_id<=a.to_node_id<=w[1] or w[1]<=a.to_node_id<=a.from_node_id<=w[0]) and param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]:
                            if a.link_type in ['ur','dr']:                            
                                y[w,a.link_seq_no]=self.__first_origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        
                            if a.link_type in ['ucd','cod']:
                                y[w,a.link_seq_no]=self.__first_origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        
                         
        
        #add constraints
        #train flow balance-starting outgoing
        node_seq_no=network.node_index_to_no_dict[(-1,-1,-1,-1)]
        self.__first_origin_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list) == param.max_unit,name="MC1[-1]")
        
        #train flow balance-ending ingoing
        node_seq_no=network.node_index_to_no_dict[(-2,-2,-2,-2)]
        self.__first_origin_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list) == param.max_unit,name="MC1[-2]")
        
        #train flow balance-inter node
        num=0
        for v in network.node_list:
            # print(v.node_id)
            if v.node_id>=0:
                self.__first_origin_model.addConstr((gb.quicksum(x[a.link_seq_no] for a in v.outgoing_link_list if a.link_type not in ['vv','vp'])
                -gb.quicksum(x[a.link_seq_no] for a in v.incoming_link_list if a.link_type not in ['vv','vp']))
                == 0,name="MC1[%d]"%(num))                
                num+=1
        
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction      
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):   
                        # tpp=tp+sec.run_time
                        if tp<param.train_latest_time[run_dir,from_node_id]+1:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                
                if len(temp_safe_node)>0:
                    self.__first_origin_model.addConstr((gb.quicksum(self.z_var[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            <= 1,name="MC2[%d,%d,%d]"%(from_node_id,t,run_dir))

                if len(temp_safe_node_max)>0:
                    self.max_const[from_node_id,t,run_dir]=self.__first_origin_model.addConstr((gb.quicksum(self.z_var[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node_max
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            >= 1,name="MC21[%d,%d,%d]"%(from_node_id,t,run_dir))          

                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                
                self.__first_origin_model.addConstr(gb.quicksum(self.z_var[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                       if link.link_type in ['ur','dr']
                                                       for l in param.level_comosition) <= 1,name="MC4[%d,%d,%d]"%(from_node_id,run_dir,t))
                
                
                self.__first_origin_model.addConstr(gb.quicksum(self.z_var[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1,name="MC41[%d,%d,%d]"%(from_node_id,run_dir,t))
                    
            for link_seq_no in (network.station_arc_run[from_node_id,run_dir] + network.uncouple_arc[from_node_id,run_dir] + network.couple_arc[from_node_id,run_dir]):
                self.__first_origin_model.addConstr(gb.quicksum(l*self.z_var[link_seq_no,l] for l in param.level_comosition) == x[link_seq_no],name="MC3[%d]"%(link_seq_no))             
                     
        
        for a in network.link_list:
            if a.link_type=='vt':
                link_seq_no=a.link_seq_no
                from_node_id=a.from_node_id
                to_node_id=a.to_node_id
                run_dir=a.link_direction
                if a.from_node_id<0:
                    self.__first_origin_model.addConstr(x[link_seq_no] == network.init_unit[run_dir,to_node_id],name="MC5[%d]"%(link_seq_no))             
                else:
                    self.__first_origin_model.addConstr(x[link_seq_no] >= network.end_unit[run_dir,from_node_id],name="MC5[%d]"%(link_seq_no))             
            
            elif a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no 
                self.__first_origin_model.addConstr(x[link_seq_no] >=
                gb.quicksum(x[temp_link.link_seq_no]+0.5*gb.quicksum(self.z_var[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no))
            
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                self.__first_origin_model.addConstr(x[link_seq_no] <=
                gb.quicksum(x[temp_link.link_seq_no]-0.5*gb.quicksum(self.z_var[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no)) 
        
        #passenger constraints
        num=0
        for w in demand.OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2
            #passenger flow balance-starting
            index_ori=(-s-100,-s-100,-s-100,-s-100)
            node_seq_no=network.node_index_to_no_dict[index_ori]
            self.const_dic[w[0],w[1],-1]=self.__first_origin_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list if a.to_node_id==s if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d,%d,%d]"%(w[0],w[1],-1))
            num+=1
            
            #passenger flow balance-starting
            index_des=(-sp-100,-sp-100,-sp-100,-sp-100)
            node_seq_no=network.node_index_to_no_dict[index_des]
            self.const_dic[w[0],w[1],-2]=self.__first_origin_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list if a.from_node_id==sp if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d,%d,%d]"%(w[0],w[1],-2))
            num+=1
            
            #passenger flow balance-inter
            for v in network.node_list:
                if v.node_id==s and v.node_attr==1 and v.node_direction==run_dir:
                    self.__first_origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['vp']                                                    
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                
                elif v.node_id==sp and (v.node_attr==1 or v.node_attr==3) and v.node_direction==run_dir:
                    self.__first_origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                  if a.link_type in ['vp']                                                                                    
                                                                                  if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                    
                elif (s<v.node_id<sp) or (sp<v.node_id<s):
                    # print(v.node_id)
                    self.__first_origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir))
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir)
                    == 0,name="MC61[%d]"%(num))
                    num+=1
        
            #cumulative constraints            
            from_node_id=s
            to_node_id=s+1 if run_dir==1 else s-1
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                self.const_dic[w[0],w[1],t]=self.__first_origin_model.addConstr(gb.quicksum(y[w,link_no] for link_no in network.ori_arc_run[w,t]
                            if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id]
                ) <= demand.demand_accum[w,t],name="MC7[%d,%d,%d]"%(w[0],w[1],t))             
      
        #passenger arc capacity
        for sec in network.section_list:
            s=sec.from_node_id
            run_dir=sec.run_direction
            for link_seq_no in (network.station_arc_run[s,run_dir] + network.uncouple_arc[s,run_dir] + network.couple_arc[s,run_dir]):                
                # print(network.link_list[link_seq_no].link_type,link_seq_no)
                # input()
                self.__first_origin_model.addConstr(gb.quicksum(y[w,link_seq_no] for w in sec.belong_OD_list
                if param.earliest_time[w,network.link_list[link_seq_no].from_node_id]<=network.link_list[link_seq_no].start_time<=param.latest_time[w,network.link_list[link_seq_no].from_node_id])
                <= x[link_seq_no]*param.single_cap,name="MC8[%d]"%(link_seq_no)) 
        
        #objective function
        self.__first_origin_model.addConstr(gb.quicksum(sec.sec_dis*self.z_var[link_no,l]*param.cost_composition[l] 
                                                    for sec in network.section_list
                                                        for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                            for l in param.level_comosition)                      
                                    +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]                                    
                                    for s in range(param.num_station)
                                        for run_dir in [1,2]
                                            for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir])))
                                    == obj_train,name="MCA")
             
        # self.__first_origin_model.addConstr(gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(y[w,link_no] for link_no in network.ori_arc_run[w,t]
                                                # if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id]))
                                                    # for w in demand.OD_list
                                                        # for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))*param.wait_pax_cost                     
                                # +gb.quicksum(y[w_p,network.vir_arc_pax[w_p]]for w_p in demand.OD_list)*param.vitual_pax_cost                           
                                     # == obj_pax,name="MCB")
                                     
        self.const_dic[-1,-1,-1]=self.__first_origin_model.addConstr(obj_pax
                                +gb.quicksum(y[w,link_no] for w in demand.OD_list
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1)
                                                        for link_no in network.ori_arc_run[w,t]
                                                if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id])*param.wait_pax_cost                     
                                -gb.quicksum(y[w_p,network.vir_arc_pax[w_p]]for w_p in demand.OD_list)*param.vitual_pax_cost                           
                                     == gb.quicksum(demand.demand_accum[w,t]
                                                    for w in demand.OD_list
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))*param.wait_pax_cost  
                                     ,name="MCB")

        self.__first_origin_model.setObjective(param.weight_pax*obj_pax+param.weight_train*obj_train,gb.GRB.MINIMIZE)
        #
        self.__first_origin_model.update()
        self.__first_origin_model.Params.outputflag=1
        
        self.__first_origin_model.Params.MIPGap=0.01
        # self.__first_origin_model.Params.TimeLimit=500
        
        # self.__first_origin_model.write("xxx33.lp")
        # input()
        
        # self.__first_origin_model.computeIIS()
        # self.__first_origin_model.write("xxx33.ilp")
        # print("model,xxx333")
        # input()
    
    def __update_varible_constraints(self,ite,sub_start_time,sub_end_time,sub_feasible_time,sub_demand_OD,sub_demand_accum):
        for a in network.link_list:
            run_dir=a.link_direction
            from_n=a.from_node_id
            st_time=a.start_time
            if a.link_type in ['ur','dr']:
                # if a.link_seq_no not in self.max_interval_links:
                for l in param.level_comosition:                    
                    if st_time in sub_feasible_time[run_dir,from_n]:
                        # print(a.link_seq_no)
                        # print(st_time,run_dir,from_n)
                        # input()
                        self.z_var[a.link_seq_no,l].ub=1
                    else:
                        self.z_var[a.link_seq_no,l].ub=0
            
            # if a.link_seq_no == 4591:
                # self.__first_origin_model.update()
                # print(ite,self.z_var[a.link_seq_no,1].ub,self.z_var[a.link_seq_no,2].ub)
                # print(sub_feasible_time[run_dir,from_n])
                # print(st_time)
                # input()
        temp=0
        for w in demand.OD_list:
            s=w[0]
            sp=w[1]
            self.const_dic[s,sp,-1].rhs=sub_demand_OD[w]+self.remain_pax[w]
            self.const_dic[s,sp,-2].rhs=sub_demand_OD[w]+self.remain_pax[w]
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                self.const_dic[s,sp,t].rhs=sub_demand_accum[w,t]+self.remain_pax[w]
                temp+=sub_demand_accum[w,t]+self.remain_pax[w]
        
        self.const_dic[-1,-1,-1].rhs=temp        
        
        for sec in network.section_list:   
            run_dir=sec.run_direction      
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1): 
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):   
                        # tpp=tp+sec.run_time
                        if tp<param.train_latest_time[run_dir,from_node_id]:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                            
                if len(temp_safe_node_max)>0 and (sub_start_time[run_dir,from_node_id]<=t<sub_end_time[run_dir,from_node_id]-5):
                    self.max_const[from_node_id,t,run_dir].rhs=1
                else:
                    if (from_node_id,t,run_dir) in self.max_const.keys():
                        self.max_const[from_node_id,t,run_dir].rhs=0
                    
        self.__first_origin_model.update()
        
        if ite==0:
            self.__first_origin_model.Params.TimeLimit=1500
        else:
            self.__first_origin_model.Params.TimeLimit=500
        
        self.__first_origin_model.optimize()
        
      
        # self.__first_origin_model.write("xxx33.lp")
        
        if self.__first_origin_model.Status == gb.GRB.INFEASIBLE or self.__first_origin_model.Status==gb.GRB.INF_OR_UNBD:
            self.__first_origin_model.computeIIS()
            self.__first_origin_model.write("xxx33.ilp")
            print("model,xxx333")
            input()

        for w in demand.OD_list:
            self.remain_pax[w]=self.y_vir[w].x
        
        # if ite==1:
            # for key in self.z_var.keys():            
                # if self.z_var[key].x>0:
                    # print(self.z_var[key].x)
                    # input()
                    
        num=0
        for key in self.z_var.keys():            
            if self.z_var[key].x>=0.9:
                link_seq_no=key[0]
                if link_seq_no not in self.feasible_link_for_bestSol:
                    self.feasible_link_for_bestSol.append(link_seq_no)
                    num+=1
        # print(num)
        
        # Output().output_result(self.__first_origin_model,"first_best_solution")
        
        # print(sub_demand_OD[(0,11)],sub_demand_accum[(0,11),10])        
        print("itration:",ite,len(self.feasible_link_for_bestSol),self.__first_origin_model.objVal)        
        # input()
        
    # second_origin_model
    def __second_origin_pro(self):
        obj_train=self.second_origin_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_train')
        obj_pax=self.second_origin_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_pax')
        x=gb.tupledict()
        y=gb.tupledict()
        for a in network.link_list:
            #train-related varibles
            if a.link_type not in ['vp','vv']:
                x[a.link_seq_no]=self.second_origin_model.addVar(lb=0,ub=a.link_cap,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
                # if a.link_seq_no in self.feasible_link_for_bestSol:
                    # x[a.link_seq_no]=self.second_origin_model.addVar(lb=0,ub=a.link_cap,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
                # else:
                    # x[a.link_seq_no]=self.second_origin_model.addVar(lb=0,ub=0,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
               
                if a.link_type in ['ur','dr']:        
                    for l in param.level_comosition:
                        if a.link_seq_no in self.feasible_link_for_bestSol:
                            self.z_v[a.link_seq_no,l]=self.second_origin_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        else:
                            self.z_v[a.link_seq_no,l]=self.second_origin_model.addVar(lb=0,ub=0,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        
                        self.ini_z_v[a.link_seq_no,l]=0
                        
                if a.link_type in ['cod','ucd']:
                    for l in param.level_comosition:
                        self.z_v[a.link_seq_no,l]=self.second_origin_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        
                        if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                            self.z_v[a.link_seq_no,l].ub=0
                        
                        self.ini_z_v[a.link_seq_no,l]=0
                        
            #pax-related varibles
            if a.link_type not in ['vt','tud','tdu','idl','ucr']:
                for w in demand.OD_list:
                    run_dir=1 if w[0]<w[1] else 2 
                    if a.link_type=='vv' and a.from_node_id==w[0] and a.to_node_id==w[1]:
                        y[w,a.link_seq_no]=self.second_origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                    elif a.link_type=='vp' and (a.from_node_id==w[1] or a.to_node_id==w[0]) and a.link_direction==run_dir:
                        y[w,a.link_seq_no]=self.second_origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                    elif a.link_type not in ['vv','vp'] and a.link_direction==run_dir:
                        if (w[0]<=a.from_node_id<=a.to_node_id<=w[1] or w[1]<=a.to_node_id<=a.from_node_id<=w[0]) and param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]:
                            if a.link_type in ['ur','dr']:                            
                                y[w,a.link_seq_no]=self.second_origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        
                            if a.link_type in ['ucd','cod']:
                                y[w,a.link_seq_no]=self.second_origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        
        
        for w in demand.OD_list:            
            step=1 if w[0]<w[1] else -1
            for s in range(w[0],w[1],step):             
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                    self.b_v[w,s,t]=self.second_origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='b[%d,%d,%d,%d]'%(w[0],w[1],s,t))
                    self.ini_b_v[w,s,t]=0
        #add constraints
        #train flow balance-starting outgoing
        node_seq_no=network.node_index_to_no_dict[(-1,-1,-1,-1)]
        self.second_origin_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list) == param.max_unit,name="MC1[-1]")
        
        #train flow balance-ending ingoing
        node_seq_no=network.node_index_to_no_dict[(-2,-2,-2,-2)]
        self.second_origin_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list) == param.max_unit,name="MC1[-2]")
        
        #train flow balance-inter node
        num=0
        for v in network.node_list:
            # print(v.node_id)
            if v.node_id>=0:
                self.second_origin_model.addConstr((gb.quicksum(x[a.link_seq_no] for a in v.outgoing_link_list if a.link_type not in ['vv','vp'])
                -gb.quicksum(x[a.link_seq_no] for a in v.incoming_link_list if a.link_type not in ['vv','vp']))
                == 0,name="MC1[%d]"%(num))                
                num+=1
        
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction      
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        # tpp=tp+sec.run_time
                        if tp<param.train_latest_time[run_dir,from_node_id]+1:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                
                if len(temp_safe_node)>0:
                    self.second_origin_model.addConstr((gb.quicksum(self.z_v[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            <= 1,name="MC2[%d,%d,%d]"%(from_node_id,t,run_dir))

                if len(temp_safe_node_max)>0:
                    if from_node_id!=5 or (from_node_id==5 and t>20): 
                        self.second_origin_model.addConstr((gb.quicksum(self.z_v[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node_max
                                                                                      for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                          if link.link_type in ['ur','dr']))
                                >= 1,name="MC21[%d,%d,%d]"%(from_node_id,t,run_dir))                 

                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                
                self.second_origin_model.addConstr(gb.quicksum(self.z_v[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                       if link.link_type in ['ur','dr']
                                                       for l in param.level_comosition) <= 1,name="MC4[%d,%d,%d]"%(from_node_id,run_dir,t))
                
                
                self.second_origin_model.addConstr(gb.quicksum(self.z_v[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1,name="MC41[%d,%d,%d]"%(from_node_id,run_dir,t))
                    
            for link_seq_no in (network.station_arc_run[from_node_id,run_dir] + network.uncouple_arc[from_node_id,run_dir] + network.couple_arc[from_node_id,run_dir]):
                self.second_origin_model.addConstr(gb.quicksum(l*self.z_v[link_seq_no,l] for l in param.level_comosition) == x[link_seq_no],name="MC3[%d]"%(link_seq_no))             
                     
        
        for a in network.link_list:
            if a.link_type=='vt':
                link_seq_no=a.link_seq_no
                from_node_id=a.from_node_id
                to_node_id=a.to_node_id
                run_dir=a.link_direction
                if a.from_node_id<0:
                    self.second_origin_model.addConstr(x[link_seq_no] == network.init_unit[run_dir,to_node_id],name="MC5[%d]"%(link_seq_no))             
                else:
                    self.second_origin_model.addConstr(x[link_seq_no] >= network.end_unit[run_dir,from_node_id],name="MC5[%d]"%(link_seq_no))             
            
            elif a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no 
                self.second_origin_model.addConstr(x[link_seq_no] >=
                gb.quicksum(x[temp_link.link_seq_no]+0.5*gb.quicksum(self.z_v[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no))
            
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                self.second_origin_model.addConstr(x[link_seq_no] <=
                gb.quicksum(x[temp_link.link_seq_no]-0.5*gb.quicksum(self.z_v[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no)) 
        
        #passenger constraints
        num=0
        for w in demand.OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2
            #passenger flow balance-starting
            index_ori=(-s-100,-s-100,-s-100,-s-100)
            node_seq_no=network.node_index_to_no_dict[index_ori]
            self.second_origin_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list if a.to_node_id==s if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d]"%(num))
            num+=1
            
            #passenger flow balance-starting
            index_des=(-sp-100,-sp-100,-sp-100,-sp-100)
            node_seq_no=network.node_index_to_no_dict[index_des]
            self.second_origin_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list if a.from_node_id==sp if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d]"%(num))
            num+=1
            
            #passenger flow balance-inter
            for v in network.node_list:
                if v.node_id==s and v.node_attr==1 and v.node_direction==run_dir:
                    self.second_origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['vp']                                                    
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                
                elif v.node_id==sp and (v.node_attr==1 or v.node_attr==3) and v.node_direction==run_dir:
                    self.second_origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                  if a.link_type in ['vp']                                                                                    
                                                                                  if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                    
                elif (s<v.node_id<sp) or (sp<v.node_id<s):
                    # print(v.node_id)
                    self.second_origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir))
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir)
                    == 0,name="MC61[%d]"%(num))
                    num+=1
        
        
            #new constraint
            for s in network.OD_station[w]:
                if s!=w[1]:
                    for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                        
                        index=(s,t,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[index]
                        self.second_origin_model.addConstr(self.b_v[w,s,t]==
                            gb.quicksum(y[w,link.link_seq_no] for link in network.node_list[node_seq_no].outgoing_link_list
                                                              if link.link_type in ['ur','dr'])
                        ,name="MC71[%d,%d,%d,%d]"%(w[0],w[1],s,t))
            
            
            #cumulative constraints            
            from_node_id=s
            to_node_id=s+1 if run_dir==1 else s-1
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                self.second_origin_model.addConstr(gb.quicksum(y[w,link_no] for link_no in network.ori_arc_run[w,t]
                            if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id]
                ) <= demand.demand_accum[w,t],name="MC7[%d,%d,%d]"%(w[0],w[1],t))             
      
        #passenger arc capacity
        for sec in network.section_list:
            s=sec.from_node_id
            run_dir=sec.run_direction
            for link_seq_no in (network.station_arc_run[s,run_dir] + network.uncouple_arc[s,run_dir] + network.couple_arc[s,run_dir]):                
                # print(network.link_list[link_seq_no].link_type,link_seq_no)
                # input()
                self.second_origin_model.addConstr(gb.quicksum(y[w,link_seq_no] for w in sec.belong_OD_list
                if param.earliest_time[w,network.link_list[link_seq_no].from_node_id]<=network.link_list[link_seq_no].start_time<=param.latest_time[w,network.link_list[link_seq_no].from_node_id])
                <= x[link_seq_no]*param.single_cap,name="MC8[%d]"%(link_seq_no)) 
        
        #objective function
        self.second_origin_model.addConstr(gb.quicksum(sec.sec_dis*self.z_v[link_no,l]*param.cost_composition[l] 
                                                    for sec in network.section_list
                                                        for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                            for l in param.level_comosition)                      
                                    +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]                                    
                                    for s in range(param.num_station)
                                        for run_dir in [1,2]
                                            for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir])))
                                    == obj_train,name="MCA")
             
        self.second_origin_model.addConstr(gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(y[w,link_no] for link_no in network.ori_arc_run[w,t]
                                                if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id]))
                                                    for w in demand.OD_list
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))*param.wait_pax_cost                     
                                +gb.quicksum(y[w_p,network.vir_arc_pax[w_p]]for w_p in demand.OD_list)*param.vitual_pax_cost                           
                                     == obj_pax,name="MCB")

        self.second_origin_model.setObjective(param.weight_pax*obj_pax+param.weight_train*obj_train,gb.GRB.MINIMIZE)
        #
        for run_dir in [1,2]:
            for s in range(param.num_station):
                if (s,run_dir) in self.last_time.keys():
                    t=self.last_time[s,run_dir]
                    for tp in range(t+1,t+2):
                        index=(s,tp,run_dir,1)
                        node_seq=network.node_index_to_no_dict[index]
                        for link in network.node_list[node_seq].outgoing_link_list:
                            if link.link_type in ["ur","dr"]:
                                for l in param.level_comosition:
                                    # print(s,tp,run_dir)
                                    self.z_v[link.link_seq_no,l].ub=0
                                    self.last_link.append((link.link_seq_no,l))
        
        
        self.second_origin_model.update()
        
        self.second_origin_model.Params.outputflag=1
        # self.second_origin_model.Params.MIPGap=0.01
        # self.second_origin_model.Params.TimeLimit=3000
        
        # self.second_origin_model.write("xxx33.lp")
        # input()
        
        # self.second_origin_model.optimize()
        
        # print("obj-pax:",param.weight_pax*obj_pax.x,"obj-train:",param.weight_train*obj_train.x)
        
        # self.second_origin_model.computeIIS()
        # self.second_origin_model.write("xxx33.ilp")
        # print("model,xxx333")
        # input()

    def __input_prePeriod_solution(self):
        with open(output_dir + '/result_ini_best_solution_7.csv', 'r', encoding='utf-8') as fp:
            reader = csv
            reader = csv.DictReader(fp)
            for line in reader:
                # print(line)
                # input()
                varName = line['varName']
                if varName is None:
                    continue
                
                link_type = line['type']
                if link_type is None:
                    continue

                from_node = _convert_str_to_int(line['from_node'])
                if from_node is None:
                    continue 

                to_node = _convert_str_to_int(line['to_node'])
                if to_node is None:
                    continue                      
                    
                from_time = _convert_str_to_int(line['from_time'])
                if from_time is None:
                    continue 

                to_time = _convert_str_to_int(line['to_time'])
                if to_time is None:
                    continue                     

                from_no = _convert_str_to_int(line['from_seq_no'])
                if from_no is None:
                    continue  

                to_no = _convert_str_to_int(line['to_seq_no'])
                if to_no is None:
                    continue
                
                value = _convert_str_to_int(line['value'])
                if value is None:
                    continue

                temp_OD = line['OD']
                flag=0
                if temp_OD is None or temp_OD=='':
                    flag=1
                else:
                    # print(temp_OD)
                    temp_OD=temp_OD[1:]
                    temp_OD=temp_OD[:-1]
                    temp_OD=temp_OD.split(",")
                    # print(temp_OD)
                    temp_OD=(int(temp_OD[0]),int(temp_OD[1]))          
                
                run_dir=1 if from_node<to_node else 2
                if link_type in ['ur','dr'] and (varName == 'x'  or varName == 'z'):                    
                    if (from_node,run_dir) in self.last_time.keys():
                        if self.last_time[from_node,run_dir]<from_time:
                            self.last_time[from_node,run_dir]=from_time
                    else:
                        self.last_time[from_node,run_dir]=from_time
                    
                if to_time == param.max_time-1:
                    if (run_dir,to_node) in network.init_unit.keys():
                        network.init_unit[run_dir,to_node]+=value
                    else:
                        network.init_unit[run_dir,to_node]=value
                                        
                if link_type in ['vv']:
                    print("there is passengers remaining!")
                    input()         


    def __input_initial_solution(self):
        
        dep_pax={} 
        pax_arc={}
        with open(output_dir + '/result_ini_best_solution_8.csv', 'r', encoding='utf-8') as fp:
            reader = csv
            reader = csv.DictReader(fp)
            for line in reader:
                # print(line)
                # input()
                varName = line['varName']
                if varName is None:
                    continue
                
                link_type = line['type']
                if link_type is None:
                    continue

                from_node = _convert_str_to_int(line['from_node'])
                if from_node is None:
                    continue 

                to_node = _convert_str_to_int(line['to_node'])
                if to_node is None:
                    continue                      
                    
                from_time = _convert_str_to_int(line['from_time'])
                if from_time is None:
                    continue  

                from_no = _convert_str_to_int(line['from_seq_no'])
                if from_no is None:
                    continue  

                to_no = _convert_str_to_int(line['to_seq_no'])
                if to_no is None:
                    continue
                
                value = _convert_str_to_int(line['value'])
                if value is None:
                    continue

                temp_OD = line['OD']
                flag=0
                if temp_OD is None or temp_OD=='':
                    flag=1
                else:
                    # print(temp_OD)
                    temp_OD=temp_OD[1:]
                    temp_OD=temp_OD[:-1]
                    temp_OD=temp_OD.split(",")
                    # print(temp_OD)
                    temp_OD=(int(temp_OD[0]),int(temp_OD[1]))          
               
                if link_type in ['ur','dr'] and (varName == 'x'  or varName == 'z'):
                    index=(from_no,to_no)
                    link_seq_no=network.link_index_to_no_dict[index]
                    
                    # if link_type in ['ur','dr'] and link_seq_no not in  self.feasible_link_for_bestSol:
                    self.feasible_link_for_bestSol.append(link_seq_no)
                 
                    for l in param.level_comosition:
                        if l==round(value):
                            # if link_seq_no==751:
                                # print(l,link_seq_no,"***")
                                # input()
                            self.ini_z_v[link_seq_no,l]=1
                            # if link_seq_no not in self.feasible_link_for_bestSol:
                                # self.feasible_link_for_bestSol.append(link_seq_no)                            
                                # break
                if flag==0:
                    d1=1 if temp_OD[0]<temp_OD[1] else 2
                    d2=1 if from_node<to_node else 2
                
                if varName[0]=='y' and flag==0 and link_type in ['ur','dr']: 
                    if temp_OD[0]==from_node and d1==d2:
                        # self.b_v[temp_OD,from_node,from_time]=max(0,value)
                        self.ini_b_v[temp_OD,from_node,from_time]=max(0,value)
        

                #FCFS的处理
                if link_type in ['ur','dr','ucr','cod'] and (varName == 'x'  or varName == 'z'):
                    index=(from_no,to_no)
                    link_seq_no=network.link_index_to_no_dict[index]
                   
                    for l in param.level_comosition:
                        if l==round(value):                          
                            pax_arc[link_seq_no]=l
                            # print(pax_arc)
                    # if from_no==3888:     
                        # print(value,to_no)
                        # input()
        # print(pax_arc)
        # input()
        self.FCFS_process(pax_arc)
                
                # #计算等待时间及分段统计等待时间长度
                # if varName[0]=='y' and flag==0 and link_type in ['ur','dr']:
                    # if int(temp_OD[0])==from_node:
                        # if ((int(temp_OD[0]),int(temp_OD[1])),from_time) not in dep_pax.keys():
                            # dep_pax[(int(temp_OD[0]),int(temp_OD[1])),from_time] = value
                        # else:
                            # dep_pax[(int(temp_OD[0]),int(temp_OD[1])),from_time] += value
            
        # acc_arr={}
        # acc_dep={}
        # for w in demand.OD_list:
            # s=w[0]
            # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                # for tp in range(t+1):
                    # if (w,t) in acc_arr.keys():
                        # acc_arr[w,t] += demand.demand_dic[w,tp]
                    # else:
                        # acc_arr[w,t] = demand.demand_dic[w,tp]
                              
                    # if (w,t) in acc_dep.keys():
                        # if (w,tp) in dep_pax.keys():
                            # acc_dep[w,t] += dep_pax[w,tp]
                        # else:
                            # acc_dep[w,t] += 0
                    # else:
                        # acc_dep[w,t] = 0
        # tot_wt=0    
        # for (w,t) in acc_arr.keys():
                # if (w,t) in acc_dep.keys():
                    # tot_wt += acc_arr[w,t]-acc_dep[w,t]                                        
                # else:
                    # tot_wt += acc_arr[w,t]
        # print("WT")
        # print(tot_wt)
        # # input()
        
        # cout_pax={}
        # for w in demand.OD_list: 
            # s=w[0]
            # cout_pax[w]=[]
            # pre_t = None
            # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                # if (w,t) in acc_arr.keys():
                    # if pre_t!=None:
                        # if acc_arr[w,t] - acc_arr[w,pre_t]>0:
                            # num_pax = acc_arr[w,t] - acc_arr[w,pre_t]
                            # # print(w,t,num_pax)
                            # # input()
                            # w_time = None
                            # for tp in range(t,param.latest_time[w,s]+1):
                                # if (w,tp) in acc_dep.keys():
                                    # if acc_dep[w,tp]>=acc_arr[w,t]:
                                        # w_time = tp-t
                                        # break
                            # if w_time != None:
                                # cout_pax[w].append((num_pax,w_time))                            
                                # pre_t = t
                    # else:
                        # if acc_arr[w,t] >0:
                            # num_pax = acc_arr[w,t]
                            # w_time = None
                            # # print(w,t,num_pax)
                            # # input()
                            # for tp in range(t,param.latest_time[w,s]+1):
                                # if (w,tp) in acc_dep.keys():
                                    # if acc_dep[w,tp]>=acc_arr[w,t]:
                                        # w_time = tp-t
                                        # break
                            # if w_time != None:
                                # cout_pax[w].append((num_pax,w_time))                            
                                # pre_t = t
        # int_pax={}
        # for w in demand.OD_list:             
            # for w_pax in cout_pax[w]:
                # int_p = w_pax[1]//5
                # if int_p in int_pax.keys():
                    # int_pax[int_p] += w_pax[0]
                # else:
                    # int_pax[int_p] = w_pax[0]
        
        # sorted_dict = dict(sorted(int_pax.items()))       
        # for item in sorted_dict.items():
            # print(item[0]*5,item[1])
        # input()
        
        
        # with open(output_dir + '/initial_obj.csv', 'r', encoding='utf-8') as fp:
            # reader = csv
            # reader = csv.DictReader(fp)
            # for line in reader:
                # # print(line)
                # # input()
                # sec_id = _convert_str_to_int(line['sec_id'])
                # if sec_id is None:
                    # continue
                
                # sec_from = _convert_str_to_int(line['sec_from'])
                # if sec_from is None:
                    # continue

                # sec_to = _convert_str_to_int(line['sec_to'])
                # if sec_to is None:
                    # continue 

                # self.sec_estimate_lower_bound[sec_id] = _convert_str_to_int(line['sec_lb'])
                # if self.sec_estimate_lower_bound[sec_id] is None:
                    # continue

                # self.estimate_lower_bound = _convert_str_to_int(line['total_lb'])
                # if self.estimate_lower_bound is None:
                    # continue                      

                # object_BAC.UB = _convert_str_to_int(line['initial_obj'])
                # if object_BAC.UB is None:
                    # continue


        # for key in self.z_v.keys():
            # link_type=network.link_list[key[0]].link_type
            # if link_type in ['ur','dr']:
                # if key[0] in self.feasible_link_for_bestSol:
                    # object_BAC.best_x_value[key[0]]=key[1]
                    # self.z_v[key].ub=1
                # else:                    
                    # self.z_v[key].ub=0
                
            # if self.z_v[key].x!=self.ini_z_v[key]:
                # print("z",key,self.z_v[key].x,self.ini_z_v[key])
                # input()
        
        # for key in self.b_v.keys():
            # if self.b_v[key].x!=self.ini_b_v[key]:
                # print("b",key,self.b_v[key].x,self.ini_b_v[key])
                # input()
        
                  
                
        # print("final:",len(self.feasible_link_for_bestSol),self.ini_b_v[(0,1),0,0])
        # input()
        
    def __defined_range(self,ite,max_ite,legth_time):
        sub_feasible_time={}
        sub_demand_OD={}
        sub_start_time={}
        sub_end_time={}
        sub_demand_accum={}
      
        start_time=ite*legth_time-5
        end_time=(ite+1)*legth_time-1
        dep1={}
        dep2={}
        for run_dir in [1,2]:
            step=1 if run_dir==1 else -1 
            s_s=0 if  run_dir==1 else param.num_station-1
            e_s=param.num_station if  run_dir==1 else -1
            for s in range(s_s,e_s,step):                
                sub_feasible_time[run_dir,s]=[] 
                if (s==0 and step==1) or (s==param.num_station-1 and step==-1):
                    if start_time>=param.train_early_time[run_dir,s]:
                        dep1[run_dir,s]=start_time
                    else:
                        dep1[run_dir,s]=param.train_early_time[run_dir,s]
                        
                    if end_time<=param.train_latest_time[run_dir,s]:
                        dep2[run_dir,s]=end_time
                    else:
                        dep2[run_dir,s]=param.train_latest_time[run_dir,s] 
                    
                    if ite==0:
                        dep1[run_dir,s]=param.train_early_time[run_dir,s]
                    if ite==max_ite-1:
                        dep2[run_dir,s]=param.train_latest_time[run_dir,s]
                        
                    for t in range(dep1[run_dir,s],dep2[run_dir,s]+1):
                        if t in self.feasible_time[run_dir,s]:
                            sub_feasible_time[run_dir,s].append(t)
                            # print(run_dir,s,t)
                            # input()
                    
                else:
                    # print(step,s,run_dir)
                    sec=network.sec_index_to_no_dict[run_dir,s-step]
                    
                    if dep1[run_dir,s-step]+sec.run_time<=param.train_latest_time[run_dir,s]:
                        dep1[run_dir,s]=dep1[run_dir,s-step]+sec.run_time
                    else:
                        dep1[run_dir,s]=param.train_latest_time[run_dir,s] 
                    
                    
                    if dep2[run_dir,s-step]+sec.run_time<=param.train_latest_time[run_dir,s]:
                        dep2[run_dir,s]=dep2[run_dir,s-step]+sec.run_time
                    else:
                        dep2[run_dir,s]=param.train_latest_time[run_dir,s]
                    
                    if ite==0:
                        dep1[run_dir,s]=param.train_early_time[run_dir,s]
                    if ite==max_ite-1:
                        dep2[run_dir,s]=param.train_latest_time[run_dir,s]
                    
                    # if s==0 and run_dir==2:
                        # print(dep1[run_dir,s],dep2[run_dir,s])
                        # input()
                    
                    for t in range(dep1[run_dir,s],dep2[run_dir,s]+1):
                        if t in self.feasible_time[run_dir,s]:
                            sub_feasible_time[run_dir,s].append(t)
                            # print(run_dir,s,t)
                            # input()
                
                flag_et=10000
                flag_lt=0
                for t in sub_feasible_time[run_dir,s]:
                    if flag_et>t:
                        flag_et=t
                    if flag_lt<t:
                        flag_lt=t            
                
                sub_start_time[run_dir,s]=flag_et
                sub_end_time[run_dir,s]=flag_lt          
        
        # print(dep2)
        
        numtest=0        
        for w in demand.OD_list:
            run_dir=1 if w[0]<w[1] else 2
            num=0
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):                
                num1=0
                if sub_start_time[run_dir,w[0]]<=t<=sub_end_time[run_dir,w[0]]:
                    num+=demand.demand_dic[w,t]
                    numtest+=demand.demand_dic[w,t]
                    
                for tp in range(sub_start_time[run_dir,w[0]],t+1):
                    if sub_start_time[run_dir,w[0]]<=tp<=sub_end_time[run_dir,w[0]]:
                        num1+=demand.demand_dic[w,tp]
                
                sub_demand_accum[w,t]=num1 

                # print(w,t,sub_demand_accum[w,t])
                # input()
                
            sub_demand_OD[w]=num

        print("ite.{},  total demand.{}.".format(ite,numtest))
        
        # if ite==2:
        # # print(sub_feasible_time[1,1])
        # print({(d,s): sub_feasible_time[d,s] for (d,s) in sub_feasible_time if s==1 and d==2})
        # # # # print(param.train_early_time)
        # # # # print(param.train_latest_time)
        # # print(sub_start_time[1,15],sub_end_time[1,15])
        # input()
        
        return sub_feasible_time,sub_demand_OD,sub_start_time,sub_end_time,sub_demand_accum
      

    def __re_defined_range(self,start_time,end_time):
        sub_feasible_time={}    
        sub_start_time={}
        sub_end_time={} 
        
        dep1={}
        dep2={}
        for run_dir in [1,2]:
            step=1 if run_dir==1 else -1 
            s_s=0 if  run_dir==1 else param.num_station-1
            e_s=param.num_station if  run_dir==1 else -1
            for s in range(s_s,e_s,step):                
                sub_feasible_time[run_dir,s]=[] 
                if (s==0 and step==1) or (s==param.num_station-1 and step==-1):
                    if start_time>=param.train_early_time[run_dir,s]:
                        dep1[run_dir,s]=start_time
                    else:
                        dep1[run_dir,s]=param.train_early_time[run_dir,s]
                        
                    if end_time<=param.train_latest_time[run_dir,s]:
                        dep2[run_dir,s]=end_time
                    else:
                        dep2[run_dir,s]=param.train_latest_time[run_dir,s] 
                    
                    # if ite==0:
                        # dep1[run_dir,s]=param.train_early_time[run_dir,s]
                    # if ite==max_ite-1:
                        # dep2[run_dir,s]=param.train_latest_time[run_dir,s]
                        
                    for t in range(dep1[run_dir,s],dep2[run_dir,s]+1):
                        if t in self.feasible_time[run_dir,s]:
                            sub_feasible_time[run_dir,s].append(t)
                            # print(run_dir,s,t)
                            # input()
                    
                else:
                    # print(step,s,run_dir)
                    sec=network.sec_index_to_no_dict[run_dir,s-step]
                    
                    if dep1[run_dir,s-step]+sec.run_time<=param.train_latest_time[run_dir,s]:
                        dep1[run_dir,s]=dep1[run_dir,s-step]+sec.run_time
                    else:
                        dep1[run_dir,s]=param.train_latest_time[run_dir,s] 
                    
                    
                    if dep2[run_dir,s-step]+sec.run_time<=param.train_latest_time[run_dir,s]:
                        dep2[run_dir,s]=dep2[run_dir,s-step]+sec.run_time
                    else:
                        dep2[run_dir,s]=param.train_latest_time[run_dir,s]
                    
                    # if ite==0:
                        # dep1[run_dir,s]=param.train_early_time[run_dir,s]
                    # if ite==max_ite-1:
                        # dep2[run_dir,s]=param.train_latest_time[run_dir,s]
                    
                    # if s==0 and run_dir==2:
                        # print(dep1[run_dir,s],dep2[run_dir,s])
                        # input()
                    
                    for t in range(dep1[run_dir,s],dep2[run_dir,s]+1):
                        if t in self.feasible_time[run_dir,s]:
                            sub_feasible_time[run_dir,s].append(t)
                            # print(run_dir,s,t)
                            # input()
                
                flag_et=10000
                flag_lt=0
                for t in sub_feasible_time[run_dir,s]:
                    if flag_et>t:
                        flag_et=t
                    if flag_lt<t:
                        flag_lt=t            
                
                sub_start_time[run_dir,s]=flag_et
                sub_end_time[run_dir,s]=flag_lt 
                
        # if ite==2:
        # # print(sub_feasible_time[1,1])
        # print({(d,s): sub_feasible_time[d,s] for (d,s) in sub_feasible_time if s==1 and d==2})
        # # # # print(param.train_early_time)
        # # # # print(param.train_latest_time)
        # # print(sub_start_time[1,15],sub_end_time[1,15])
        # input()
        
        return sub_feasible_time

    def FCFS_process(self,pax_arc):
        
        dep_pax={}
        temp_pax_arc={}
        remain_pax={}
        for link_seq in pax_arc.keys():
            temp_pax_arc[link_seq]=pax_arc[link_seq]*param.single_cap
            
            # if network.link_list[link_seq].from_node_seq_no==3888:
                # print(link_seq,network.link_list[link_seq].from_node_seq_no,network.link_list[link_seq].to_node_seq_no)
                # print(network.link_list[link_seq].from_node_id,network.link_list[link_seq].to_node_id)
                # input()
        # input()
        # print(pax_arc)
        # input()
        
        for r_dir in [1,2]:
            if r_dir == 1: #上行方向
                start_s=0
                end_s=param.num_station
                step=1
            else: #下行方向(-1)
                start_s=param.num_station-1
                end_s=-1
                step=-1
            
            # print(start_s,end_s,step)
            # input()
            for s in range(start_s,end_s,step):
                for t in range(param.train_early_time[r_dir,s],param.train_latest_time[r_dir,s]+1):
                    for sp in range(end_s-step,s,-step):
                        w=(s,sp)
                        # if sp==11:
                            # print(s,step,r_dir)
                            # input()
                        if param.earliest_time[w,s]<=t<=param.latest_time[w,s]:
                            if (w,t) in demand.demand_dic.keys():
                                for tp in range(t,param.latest_time[w,s]+1):
                                    n_index=(s,tp,r_dir,1)                                
                                    node_seq=network.node_index_to_no_dict[n_index]
                                    
                                    node=network.node_list[node_seq]
                                    
                                    temp_link_list=[]
                                    min_flow=99999999
                                    flag=False
                                    # if w==(0,11):
                                        # print(w,t,tp,node_seq)
                                        # input()
                                    while True:
                                        flag_break=True
                                        for link in node.outgoing_link_list:
                                            # if w==(0,11):
                                                # print(link.from_node_seq_no,link.to_node_seq_no)
                                            if link.link_seq_no in temp_pax_arc.keys():
                                                # if link.from_node_seq_no==3888:
                                                    # print(link.to_node_seq_no)
                                                    # print(w)
                                                    # input()
                                                # if w==(0,11):
                                                    # print(link.to_node_seq_no)
                                                    # print(w)
                                                    # input()
                                                    # print(link.from_node_seq_no,link.to_node_seq_no)
                                                    # print(link.link_type,link.from_node_id,link.to_node_id)
                                                    # print()
                                                    # input()
                                                if temp_pax_arc[link.link_seq_no]<min_flow:
                                                    min_flow = temp_pax_arc[link.link_seq_no]
                                                temp_link_list.append(link)
                                                
                                                # if node_seq==14:
                                                    # print(node_seq)
                                                    # print(temp_link_list)
                                                    # input()
                                                    
                                                if link.to_node_id == sp:
                                                    flag=True
                                                    break
                                                to_node_seq = link.to_node_seq_no
                                                node=network.node_list[to_node_seq]
                                                
                                                # if node_seq==14:
                                                    # print(to_node_seq)
                                                    # input()
                                            
                                                flag_break=False
                                        
                                        # if node_seq==14:
                                            # print(node_seq,flag_break,flag)
                                            # print(temp_link_list)
                                            # input()
                                        
                                        if flag_break==True:
                                            break
                                            
                                    # if w==(0,11):
                                        # print(w,t,tp,node_seq,flag)
                                        # print(temp_link_list)
                                        # input()
                                    
                                    if flag==True:                                    
                                        load_pax=None
                                        re_pax=remain_pax[w,t] if (w,t) in remain_pax.keys() else 0
                                        
                                        if demand.demand_dic[w,t]+re_pax<=min_flow:
                                            load_pax=demand.demand_dic[w,t]+re_pax
                                        else:
                                            load_pax=min_flow
                                            if (w,t+1) in remain_pax.keys():
                                                remain_pax[w,t+1]+=demand.demand_dic[w,t]-min_flow
                                            else:
                                                remain_pax[w,t+1]=demand.demand_dic[w,t]-min_flow
                                            # print(w,demand.demand_dic[w,t]-min_flow)
                                            # input()
                                        
                                        for link in temp_link_list:
                                            if temp_pax_arc[link.link_seq_no]-load_pax<=0.01:
                                                del temp_pax_arc[link.link_seq_no]  
                                            else:
                                                temp_pax_arc[link.link_seq_no]=temp_pax_arc[link.link_seq_no]-load_pax
                                        
                                        if (w,tp) not in dep_pax.keys():
                                            dep_pax[w,tp]=load_pax
                                        else:
                                            dep_pax[w,tp]+=load_pax
                                        break

        # for item in dep_pax.keys():
            # if dep_pax[item]>0 and item[0]==(10,0):
                # print(item,dep_pax[item])                
        # input()
        
        
        acc_arr={}
        acc_dep={}
        for w in demand.OD_list:
            s=w[0]
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                for tp in range(t+1):
                    if (w,t) in acc_arr.keys():
                        acc_arr[w,t] += demand.demand_dic[w,tp]
                    else:
                        acc_arr[w,t] = demand.demand_dic[w,tp]
                              
                    if (w,t) in acc_dep.keys():
                        if (w,tp) in dep_pax.keys():
                            acc_dep[w,t] += dep_pax[w,tp]
                        else:
                            acc_dep[w,t] += 0
                    else:
                        acc_dep[w,t] = 0
        tot_wt=0    
        for (w,t) in acc_arr.keys():
                if (w,t) in acc_dep.keys():
                    tot_wt += acc_arr[w,t]-acc_dep[w,t]                                        
                else:
                    tot_wt += acc_arr[w,t]
        print("WT")
        print(tot_wt)
        # input()
        
        cout_pax={}
        for w in demand.OD_list: 
            s=w[0]
            cout_pax[w]=[]
            pre_t = None
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                if (w,t) in acc_arr.keys():
                    if pre_t!=None:
                        if acc_arr[w,t] - acc_arr[w,pre_t]>0:
                            num_pax = acc_arr[w,t] - acc_arr[w,pre_t]
                            # print(w,t,num_pax)
                            # input()
                            w_time = None
                            for tp in range(t,param.latest_time[w,s]+1):
                                if (w,tp) in acc_dep.keys():
                                    if acc_dep[w,tp]>=acc_arr[w,t]:
                                        w_time = tp-t
                                        break
                            if w_time != None:
                                cout_pax[w].append((num_pax,w_time))                            
                                pre_t = t
                    else:
                        if acc_arr[w,t] >0:
                            num_pax = acc_arr[w,t]
                            w_time = None
                            # print(w,t,num_pax)
                            # input()
                            for tp in range(t,param.latest_time[w,s]+1):
                                if (w,tp) in acc_dep.keys():
                                    if acc_dep[w,tp]>=acc_arr[w,t]:
                                        w_time = tp-t
                                        break
                            if w_time != None:
                                cout_pax[w].append((num_pax,w_time))                            
                                pre_t = t
        int_pax={}
        for w in demand.OD_list:             
            for w_pax in cout_pax[w]:
                int_p = w_pax[1]//5
                if int_p in int_pax.keys():
                    int_pax[int_p] += w_pax[0]
                else:
                    int_pax[int_p] = w_pax[0]
        
        sorted_dict = dict(sorted(int_pax.items()))       
        for item in sorted_dict.items():
            print(item[0]*5,item[1])
        input()        

    def process(self):
        # # # estimate lower bound
        # self.__train_lower_bound_new()
        # self.__train_lower_bound()
        
        # # ###使用两个下界提升的不等式
        self.__train_lower_bound_OD()
        self.__train_lower_bound_OD_WT()
        # input()
        
        # #分段求解可行解
        # legth_time=10
        # max_ite=math.ceil(param.max_time/legth_time)
        # remain_demand={}
        # sec_remain_demand={}
        # for w in demand.OD_list:
            # remain_demand[w]=0
            # sec_remain_demand[w]=0
        # print(max_ite)
        # # input()
        # self.__ite_first_origin_pro()
        # for ite in range(max_ite):
            # #划分时段范围+划分需求
            # sub_feasible_time,sub_demand_OD,sub_start_time,sub_end_time,sub_demand_accum=self.__defined_range(ite,max_ite,legth_time)        
            # self.__update_varible_constraints(ite,sub_start_time,sub_end_time,sub_feasible_time,sub_demand_OD,sub_demand_accum)
        
        
        # with open(output_dir + "/result_fist_stage_feasLink.csv", "w", newline="") as fp:
            # writer = csv.writer(fp)
        
            # temp=['varName','type','from_node','to_node','from_time','to_time','from_seq_no','to_seq_no','value']
            # writer.writerow(temp)        
        
            # for link_seq_no in self.feasible_link_for_bestSol:
                # temp=[]              
                # val=1
                # temp.append('z')
                # temp.append(network.link_list[link_seq_no].link_type)
                # temp.append(network.link_list[link_seq_no].from_node_id)
                # temp.append(network.link_list[link_seq_no].to_node_id)
                # from_node_seq_no=network.link_list[link_seq_no].from_node_seq_no
                # to_node_seq_no=network.link_list[link_seq_no].to_node_seq_no                        
                # temp.append(network.node_list[from_node_seq_no].node_time)
                # temp.append(network.node_list[to_node_seq_no].node_time)
                # temp.append(from_node_seq_no)
                # temp.append(to_node_seq_no)
                # temp.append(val)
                # # input()
                
                # # if from_node_seq_no==4 and to_node_seq_no==248:
                    # # print(link_seq_no)
                    # # input()
                
                # if len(temp)>0:
                    # writer.writerow(temp) 
        # print("outputS1 successfull!")
        # input()
        
        # self.__second_origin_pro()
        
        # # self.z_v[4591,1].lb=1
        # self.second_origin_model.update()
        
        # self.second_origin_model.optimize()
        
        
        # # self.second_origin_model.optimize()
        # # self.second_origin_model.computeIIS()
        # # self.second_origin_model.write("xxx33.ilp")
        # # print("model,xxx333")        
        # # input()
        
        
        # # self.ini_b_v = {key: var.X for key, var in self.b_v.items()}
        # # self.ini_z_v = {key: var.X for key, var in self.z_v.items()}
        
               
        
        # # self.feasible_link_for_bestSol=[]       
        # # for key in self.z_v.keys():            
            # # if self.z_v[key].x>0.9:
                # # self.z_v[key].ub=1
                # # self.feasible_link_for_bestSol.append(key[0])
            # # else:
                # # self.z_v[key].ub=0
                
            # # if self.ini_z_v[key]==1:
                # # print(key,self.ini_z_v[key])
                # # input()
        
        # # for key in self.b_v.keys():
            # # print(self.ini_b_v[key])
            # # input()
        
        # Output().output_result(self.second_origin_model,"ini_second_stage_best_solution")
        # print("final:",len(self.feasible_link_for_bestSol))        
                
        # # # # #输出初始解
        # object_BAC.UB=self.second_origin_model.objVal
        # # print("object_BAC.UB:",object_BAC.UB)
        # with open(output_dir + "/initial_obj.csv", "w", newline="") as fp:
            # writer = csv.writer(fp)
        
            # temp=['sec_id','sec_from','sec_to','sec_lb','total_lb','initial_obj']
            # writer.writerow(temp)
            # num=0
            # for sec in network.section_list:
                # temp=[]
                # temp.append(sec.section_id)
                # temp.append(sec.from_node_id)
                # temp.append(sec.to_node_id)
                # temp.append(self.sec_estimate_lower_bound[sec.section_id])
                # if num==0:
                    # temp.append(self.estimate_lower_bound)
                    # temp.append(object_BAC.UB)
                # num += 1
            
                # if len(temp)>0:
                    # writer.writerow(temp)
        
        # self.second_origin_model.update()
        # print("outputS2 successfull!")
        # input()
        
        
        # # # # # #直接输入初始解 垂直启发式        
        
        # self.__input_initial_solution()
        # self.__second_origin_pro()
        
        # # object_BAC.UB=85147.41
        
        # for key in self.z_v.keys():
            # link_type=network.link_list[key[0]].link_type
            # from_time=network.link_list[key[0]].start_time
            # if 0<=from_time<=120 and link_type in ['cod','ucd']:
                # self.z_v[key].ub=1
        
        # time_gap=3
        # num_link=0
        # # for d_r in [1,2]:
        # d_r=2
        # for link_seq_no in self.feasible_link_for_bestSol:   
            # a=network.link_list[link_seq_no]
            # if a.link_type in ['ur','dr']:  
                # s=a.from_node_id
                # sp=a.to_node_id
                # run_dir=a.link_direction
                # from_time=a.start_time
                # run_time=a.end_time-a.start_time
                # if run_dir==d_r:
                    # if param.train_early_time[run_dir,s]+50<=from_time<=param.train_early_time[run_dir,s]+60:
                        # for t in range(max(from_time-time_gap,param.train_early_time[run_dir,s]),min(from_time+time_gap,param.train_latest_time[run_dir,s])+1):
                            # from_index=(s,t,run_dir,1)
                            # tp=t+run_time
                            # if tp<=param.train_latest_time[run_dir,sp]:
                                # for v_type in [1,2,3]:
                                    # to_index=(sp,tp,run_dir,v_type)
                                    # from_seq=None;to_seq=None
                                    # if from_index in network.node_index_to_no_dict.keys():
                                        # from_seq=network.node_index_to_no_dict[from_index]
                                    # if to_index in network.node_index_to_no_dict.keys():
                                        # to_seq=network.node_index_to_no_dict[to_index]
                                   
                                    
                                    # if from_seq!=None and to_seq!=None:
                                        # link_index=(from_seq,to_seq)                                
                                        # if link_index in network.link_index_to_no_dict.keys():
                                            # temp_link_seq_no=network.link_index_to_no_dict[link_index]
                                            # for l in param.level_comosition:
                                                # # if self.z_v[temp_link_seq_no,l].lb==1:
                                                    # # print(self.z_v[temp_link_seq_no,l].ub,self.z_v[temp_link_seq_no,l].lb)
                                                    # # input()
                                                # self.z_v[temp_link_seq_no,l].ub=1
                                            
                                            # if temp_link_seq_no not in self.feasible_link_for_bestSol:
                                                        # num_link+=1
              
            
        # self.second_origin_model.update()
        # # print("final:",len(self.feasible_link_for_bestSol))
        # # # input()        
        # self.second_origin_model.Params.TimeLimit=1500
        # self.second_origin_model.optimize()
        
        
        # # # self.second_origin_model.computeIIS()
        # # # self.second_origin_model.write("xxx33.ilp")
        # # # print("model,xxx333")
        # # # input()
        
        # Output().output_result(self.second_origin_model,"ini_best_solution_new")


        # # # #Re  #直接输入初始解 倾斜启发式       
        
        # self.__input_initial_solution()
        # self.__second_origin_pro()
  
        # # # object_BAC.UB=85147.41
        
        # for key in self.z_v.keys():
            # link_type=network.link_list[key[0]].link_type
            # from_time=network.link_list[key[0]].start_time
            # if 0<=from_time<=120 and link_type in ['cod','ucd']:
                # self.z_v[key].ub=1
        
        # time_gap=3
        # num_link=0
        # # for d_r in [1,2]:
        # d_r=2
        # for link_seq_no in self.feasible_link_for_bestSol:   
            # a=network.link_list[link_seq_no]
            # if a.link_type in ['ur','dr']:  
                # s=a.from_node_id
                # sp=a.to_node_id
                # run_dir=a.link_direction
                # from_time=a.start_time
                # run_time=a.end_time-a.start_time
                # if run_dir==d_r:
                    # sub_feasible_time=self.__re_defined_range(param.train_early_time[run_dir,s]+60,param.train_early_time[run_dir,s]+90)
                    # if from_time in sub_feasible_time[run_dir,s]:
                    # # if param.train_early_time[run_dir,s]+50<=from_time<=param.train_early_time[run_dir,s]+60:
                        # for t in range(max(from_time-time_gap,param.train_early_time[run_dir,s]),min(from_time+time_gap,param.train_latest_time[run_dir,s])+1):
                            # from_index=(s,t,run_dir,1)
                            # tp=t+run_time
                            # if tp<=param.train_latest_time[run_dir,sp]:
                                # for v_type in [1,2,3]:
                                    # to_index=(sp,tp,run_dir,v_type)
                                    # from_seq=None;to_seq=None
                                    # if from_index in network.node_index_to_no_dict.keys():
                                        # from_seq=network.node_index_to_no_dict[from_index]
                                    # if to_index in network.node_index_to_no_dict.keys():
                                        # to_seq=network.node_index_to_no_dict[to_index]
                                   
                                    
                                    # if from_seq!=None and to_seq!=None:
                                        # link_index=(from_seq,to_seq)                                
                                        # if link_index in network.link_index_to_no_dict.keys():
                                            # temp_link_seq_no=network.link_index_to_no_dict[link_index]
                                            # for l in param.level_comosition:
                                                # # if self.z_v[temp_link_seq_no,l].lb==1:
                                                    # # print(self.z_v[temp_link_seq_no,l].ub,self.z_v[temp_link_seq_no,l].lb)
                                                    # # input()
                                                # self.z_v[temp_link_seq_no,l].ub=1
                                            
                                            # if temp_link_seq_no not in self.feasible_link_for_bestSol:
                                                        # num_link+=1
              
            
        # self.second_origin_model.update()
        # # print("final:",len(self.feasible_link_for_bestSol))
        # # # input()        
        # self.second_origin_model.Params.TimeLimit=1500
        # self.second_origin_model.optimize()
    
        
        # # # self.second_origin_model.computeIIS()
        # # # self.second_origin_model.write("xxx33.ilp")
        # # # print("model,xxx333")
        # # # input()
        
        # Output().output_result(self.second_origin_model,"ini_best_solution_new")

        
        print("finish initial inputs!")
        input()

class Benders_BAC_multcuts:#分解为主问题和若干个客流加载子问题
    def __init__(self):
        self.OD_node={}
        self.dual_pi_OD={}
        self.dual_lambda=gb.tupledict()
        self.dual_gamma=gb.tupledict()       
        self.b_variable=gb.tupledict()
        self.z_variable=gb.tupledict()
        
        self.OD_node_n={}
        self.dual_pi_OD_n={}
        self.dual_lambda_n=gb.tupledict()
        self.dual_gamma_n=gb.tupledict()  
        self.obj_dual_n=None
        self.dual_sub_model_n=gb.Model("dual_model")
  
  
        self.obj_dual={}
        self.obj_train=None
        self.obj_theta={}
        self.__master_model=gb.Model("master_model")
        self.__pre_master_model=gb.Model("pre_master_model")
        self.dual_sub_model={}        
        for w in demand.OD_list:
            self.dual_sub_model[w]=gb.Model("sub_model_"+str(w))
         
    
        self.LB=float('-inf')
        self.UB=float('inf')
                
        self.waiting_time={}
        self.vitual_time={}
                
        self.best_x_value={}
   
    def __reformulated_master_model(self):                
        obj_train=self.__pre_master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_train')
        
        x=gb.tupledict()
        z_variable=gb.tupledict()
        b_variable=gb.tupledict()
        for a in network.link_list:
            #train-related varibles
            if a.link_type not in ['vp','vv']:
                x[a.link_seq_no]=self.__pre_master_model.addVar(lb=0,ub=a.link_cap,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
                if a.link_type in ['ur','dr','cod','ucd']:        
                    for l in param.level_comosition:
                        z_variable[a.link_seq_no,l]=self.__pre_master_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        # z_variable[a.link_seq_no,l].lb = round(object_INI.z_v[a.link_seq_no,l])
                        # z_variable[a.link_seq_no,l].ub = round(object_INI.z_v[a.link_seq_no,l])

        for t in range(param.max_time-param.couple_time,param.max_time):
            for s in network.turnback_station_list:
                if s not in [0,param.num_station-1]:
                    for run_dir in [1,2]:
                        index=(s,t,run_dir,2)
                        node_seq=network.node_index_to_no_dict[index]
                        for link in network.node_list[node_seq].incoming_link_list:
                            if link.link_type in ['dr','ur']:
                                x[link.link_seq_no].ub=0
                        
        for w in demand.OD_list:            
            step=1 if w[0]<w[1] else -1
            for s in range(w[0],w[1],step):             
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                    b_variable[w,s,t]=self.__pre_master_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='b[%d,%d,%d,%d]'%(w[0],w[1],s,t))

        #add constraints
        #train flow balance-starting outgoing
        node_seq_no=network.node_index_to_no_dict[(-1,-1,-1,-1)]
        self.__pre_master_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list) == param.max_unit,name="MC1[-1]")
        
        #train flow balance-ending ingoing
        node_seq_no=network.node_index_to_no_dict[(-2,-2,-2,-2)]
        self.__pre_master_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list) == param.max_unit,name="MC1[-2]")
        
        #train flow balance-inter node
        num=0
        for v in network.node_list:
            # if num==519:
                # print(v.node_id,v.node_time,v.node_attr,v.node_direction)
                # input()
            if v.node_id>=0:
                self.__pre_master_model.addConstr((gb.quicksum(x[a.link_seq_no] for a in v.outgoing_link_list if a.link_type not in ['vv','vp'])
                -gb.quicksum(x[a.link_seq_no] for a in v.incoming_link_list if a.link_type not in ['vv','vp']))
                == 0,name="MC1[%d]"%(num))                
                num+=1
        
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction      
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        # tpp=tp+sec.run_time
                        if tp<param.train_latest_time[run_dir,from_node_id]+1:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                
                if len(temp_safe_node)>0:
                    self.__pre_master_model.addConstr((gb.quicksum(z_variable[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            <= 1,name="MC2[%d,%d,%d]"%(from_node_id,t,run_dir))
                                
                if len(temp_safe_node_max)>0:
                    self.__pre_master_model.addConstr((gb.quicksum(z_variable[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node_max
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            >= 1,name="MC21[%d,%d,%d]"%(from_node_id,t,run_dir))          
                    # print(from_node_id,t,run_dir)
                    # print(temp_safe_node_max)
                    # input()

                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                
                self.__pre_master_model.addConstr(gb.quicksum(z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                       if link.link_type in ['ur','dr']
                                                       for l in param.level_comosition) <= 1,name="MC4[%d,%d,%d]"%(from_node_id,run_dir,t))
                
                
                self.__pre_master_model.addConstr(gb.quicksum(z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1,name="MC41[%d,%d,%d]"%(from_node_id,run_dir,t))
                    
            for link_seq_no in (network.station_arc_run[from_node_id,run_dir] + network.uncouple_arc[from_node_id,run_dir] + network.couple_arc[from_node_id,run_dir]):
            # for link_seq_no in (network.station_arc_run[from_node_id,run_dir]):            
                self.__pre_master_model.addConstr(gb.quicksum(l*z_variable[link_seq_no,l] for l in param.level_comosition) == x[link_seq_no],name="MC3[%d]"%(link_seq_no))             
            
        
        for a in network.link_list:
            if a.link_type=='vt':
                link_seq_no=a.link_seq_no
                from_node_id=a.from_node_id
                to_node_id=a.to_node_id
                run_dir=a.link_direction
                if a.from_node_id<0:
                    self.__pre_master_model.addConstr(x[link_seq_no] == network.init_unit[run_dir,to_node_id],name="MC5[%d]"%(link_seq_no))             
                else:
                    self.__pre_master_model.addConstr(x[link_seq_no] >= network.end_unit[run_dir,from_node_id],name="MC5[%d]"%(link_seq_no))             
            
            elif a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no 
                self.__pre_master_model.addConstr(x[link_seq_no] >=
                gb.quicksum(x[temp_link.link_seq_no]+0.5*gb.quicksum(z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no))
            
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                self.__pre_master_model.addConstr(x[link_seq_no] <=
                gb.quicksum(x[temp_link.link_seq_no]-0.5*gb.quicksum(z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no)) 
        
        #passenger constraints       
        for w in demand.OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2        
            #cumulative constraints            
            from_node_id=s
            to_node_id=s+1 if run_dir==1 else s-1
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                self.__pre_master_model.addConstr(gb.quicksum(b_variable[w,s,tp] for tp in range(t+1)
                            if param.earliest_time[w,s]<=tp<=param.latest_time[w,s])
                            <= demand.demand_accum[w,t],name="MC7[%d,%d,%d]"%(w[0],w[1],t))             
        
        y=gb.tupledict()
        for a in network.link_list:           
            #pax-related varibles
            if a.link_type not in ['vt','tud','tdu','idl','ucr']:
                for w in demand.OD_list:
                    run_dir=1 if w[0]<w[1] else 2 
                    if a.link_type=='vv' and a.from_node_id==w[0] and a.to_node_id==w[1]:
                        y[w,a.link_seq_no]=self.__pre_master_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                    elif a.link_type=='vp' and (a.from_node_id==w[1] or a.to_node_id==w[0]) and a.link_direction==run_dir:
                        y[w,a.link_seq_no]=self.__pre_master_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                    elif a.link_type not in ['vv','vp'] and a.link_direction==run_dir:
                        if (w[0]<=a.from_node_id<=a.to_node_id<=w[1] or w[1]<=a.to_node_id<=a.from_node_id<=w[0]) and param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]:
                            if a.link_type in ['ur','dr']:
                                y[w,a.link_seq_no]=self.__pre_master_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        
                            if a.link_type in ['ucd','cod']:
                                y[w,a.link_seq_no]=self.__pre_master_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        

        # y[(0,2),1414].lb=18
        # y[(0,2),1414].ub=18

        # #passenger arc capacity
        # for sec in network.section_list:
            # s=sec.from_node_id
            # run_dir=sec.run_direction
            # for link_seq_no in (network.station_arc_run[s,run_dir] + network.uncouple_arc[s,run_dir] + network.couple_arc[s,run_dir]):                
                # self.__pre_master_model.addConstr(gb.quicksum(y[w,link_seq_no] for w in sec.belong_OD_list
                    # if param.earliest_time[w,network.link_list[link_seq_no].from_node_id]<=network.link_list[link_seq_no].start_time<=param.latest_time[w,network.link_list[link_seq_no].from_node_id])
                    # <= x[link_seq_no]*param.single_cap,name="MC8[%d]"%(link_seq_no))


        #passenger arc capacity
        for sec in network.section_list:
            s=sec.from_node_id
            run_dir=sec.run_direction
            for link_seq_no in (network.station_arc_run[s,run_dir] + network.uncouple_arc[s,run_dir] + network.couple_arc[s,run_dir]):                
                for w in sec.belong_OD_list:
                    if param.earliest_time[w,network.link_list[link_seq_no].from_node_id]<=network.link_list[link_seq_no].start_time<=param.latest_time[w,network.link_list[link_seq_no].from_node_id]:
                        self.__pre_master_model.addConstr(y[w,link_seq_no]
                            <= x[link_seq_no]*param.single_cap,name="MC8[%d,%d,%d]"%(w[0],w[1],link_seq_no))
        
        #passenger arc capacity for vertex // new constraint
        for sec in network.section_list:
            s=sec.from_node_id
            run_dir=sec.run_direction
            for t in range(param.train_latest_time[run_dir,s]+1): 
                node_index=(s,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                self.__pre_master_model.addConstr(gb.quicksum(b_variable[w,s,t] for w in sec.belong_OD_list
                    if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                    <= gb.quicksum(x[link.link_seq_no]*param.single_cap
                        for link in network.node_list[node_seq_no].outgoing_link_list
                        if link.link_type in ['ur','dr']),name="MC8[%d,%d,%d,%d]"%(s,run_dir,t,1))
        
        #passenger constraints
        num=0
        for w in demand.OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2
            #passenger flow balance-starting
            index_ori=(-s-100,-s-100,-s-100,-s-100)
            node_seq_no=network.node_index_to_no_dict[index_ori]
            self.__pre_master_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list if a.to_node_id==s if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d]"%(num))
            num+=1
            
            #passenger flow balance-starting
            index_des=(-sp-100,-sp-100,-sp-100,-sp-100)
            node_seq_no=network.node_index_to_no_dict[index_des]
            self.__pre_master_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list if a.from_node_id==sp if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d]"%(num))
            num+=1
            
            #passenger flow balance-inter
            for v in network.node_list:
                if v.node_id==s and v.node_attr==1 and v.node_direction==run_dir:
                    self.__pre_master_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['vp']                                                    
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                
                elif v.node_id==sp and (v.node_attr==1 or v.node_attr==3) and v.node_direction==run_dir:
                    self.__pre_master_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                  if a.link_type in ['vp']                                                                                    
                                                                                  if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','cod','ucd']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                    
                elif (s<v.node_id<sp) or (sp<v.node_id<s):
                    # print(v.node_id)
                    self.__pre_master_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir))
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir)
                    == 0,name="MC61[%d]"%(num))
                    num+=1
                
                if v.node_attr==1 and v.node_direction==run_dir and (s<v.node_id<sp or sp<v.node_id<s):
                    ts=v.node_id
                    tt=v.node_time
                    
                    if param.earliest_time[w,ts]<=tt<=param.latest_time[w,ts]:
                        temp_link_list=[]
                        for link in v.incoming_link_list:
                            if link.link_type in ['dr','ur']:
                                temp_link_list.append(link)
                            elif link.link_type in ['cod','ucd']:
                                from_node_seq_no=link.from_node_seq_no
                                
                                for t_link in network.node_list[from_node_seq_no].incoming_link_list:
                                    if t_link.link_type in ['dr','ur']:
                                        temp_link_list.append(t_link)
                                
                        #new constraint
                        if len(temp_link_list)>0:
                            for temp_link in temp_link_list:
                                from_node=temp_link.from_node_seq_no
                                pre_s=network.node_list[from_node].node_id
                                pre_t=network.node_list[from_node].node_time
                                
                                # if w==(0,4) and ts==2 and tt==8:
                                    # print(temp_link.link_seq_no,w,pre_s,pre_t)
                                    # input()
                                
                                if param.earliest_time[w,pre_s]<=pre_t<=param.latest_time[w,pre_s]:
                                    self.__pre_master_model.addConstr(b_variable[w,ts,tt]>=
                                        (gb.quicksum(z_variable[temp_link.link_seq_no,l] for l in param.level_comosition)-1)*demand.demand_OD[w]+b_variable[w,pre_s,pre_t]
                                        ,name="MC611[%d]"%(temp_link.link_seq_no))
                        # # else:
                            # # print("...",v.node_attr,v.node_id,v.node_time,v.node_direction)
                            # # input()
            
            #new constraint
            for s in network.OD_station[w]:
                if s!=w[1]:
                    for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                        
                        index=(s,t,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[index]
                        self.__pre_master_model.addConstr(b_variable[w,s,t]==
                            gb.quicksum(y[w,link.link_seq_no] for link in network.node_list[node_seq_no].outgoing_link_list
                                                              if link.link_type in ['ur','dr'])
                        ,name="MC71[%d,%d,%d,%d]"%(w[0],w[1],s,t))
        
        #objective function
        self.__pre_master_model.addConstr(gb.quicksum(sec.sec_dis*z_variable[link_no,l]*param.cost_composition[l] 
                                                    for sec in network.section_list
                                                        for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                            for l in param.level_comosition)
                                    +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]                                    
                                    for s in range(param.num_station)
                                        for run_dir in [1,2]
                                            for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir])))
                                    == obj_train,name="MCA")

        obj_pax=self.__pre_master_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_pax')
        self.__pre_master_model.addConstr(gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(y[w,link_no] for link_no in network.ori_arc_run[w,t]
                                                if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id]))
                                                    for w in demand.OD_list
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))*param.wait_pax_cost                     
                                +gb.quicksum(y[w_p,network.vir_arc_pax[w_p]]for w_p in demand.OD_list)*param.vitual_pax_cost                           
                                     == obj_pax,name="MCB")
        
        self.__pre_master_model.setObjective(param.weight_pax*obj_pax+param.weight_train*obj_train,gb.GRB.MINIMIZE)
        
        
        
        self.__pre_master_model.update()
        self.__pre_master_model.params.outputflag = 1
        # self.__pre_master_model.Params.MIPGap=0.05
        # self.__pre_master_model.params.FeasibilityTol=0.0001
        
        self.__pre_master_model.optimize()
        
        
        # self.__pre_master_model.computeIIS()
        # self.__pre_master_model.write("xxx33.ilp")
        # input()
        
        
        print(param.weight_pax*obj_pax.x,param.weight_train*obj_train.x)
        
        num=0        
        num3=0
        for w in demand.OD_list:
            num2=0
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                num1=0
                num2+=b_variable[w,w[0],t].x
                for tp in range(param.earliest_time[w,w[0]],t+1):
                    num1+=b_variable[w,w[0],tp].x
                num+=demand.demand_accum[w,t]-num1
                                       
            num3+=demand.demand_OD[w]-num2
            
        print(num,num3)
        print(num3*1000+num)
        
        
        for w in demand.OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2
            step=1 if run_dir==1 else -1
            
            print("w",w)
            for sb in range(s,sp,step):
                for t in range(param.earliest_time[w,sb],param.latest_time[w,sb]+1):
                    if b_variable[w,sb,t].x>0:
                        print(w,sb,t,b_variable[w,sb,t].x)
            
            # if w==(0,2):
                # for link_seq_no in [1414,863,974,336,1739]:
                    # print("y:",link_seq_no,y[w,link_seq_no].x)
                    # for l in [3,6]:
                        # if link_seq_no not in [1739,1414]:
                            # print("x:",link_seq_no,l,z_variable[link_seq_no,l].x)
                
            input()
       
        
        # for a in network.link_list:
            # if a.link_type in ['ur','dr','cod','ucd']:        
                # for l in param.level_comosition:
                    # self.z_variable[a.link_seq_no,l].start = round(z_variable[a.link_seq_no,l].x)
        
        for w in demand.OD_list:
            # s=w[0]      
            # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                # self.b_variable[w,t].start = b_variable[w,t].x
            print("1:",w,demand.demand_OD[w],y[w,network.vir_arc_pax[w]].x)
            
            # num=0
            # for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1): 
                # num+=self.b_variable[w,w[0],t].x
            # print("2:",w,demand.demand_OD[w],demand.demand_OD[w]-num)
            # input()
        # for key in b_variable.keys():
            # print(key)
            # print(self.b_variable[key].x,b_variable[key].x)
            # input()
        # for w in demand.OD_list:            
            # step=1 if w[0]<w[1] else -1
            # run_dir=1 if w[0]<w[1] else 2
            # # for s in range(w[0],w[1],step): 
            # s=w[0]            
            # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1): 
                # print(w,s,t)
                # node=(s,t,run_dir,1)
                # node_seq=network.node_index_to_no_dict[node]
                # num=0
                # for link in network.node_list[node_seq].outgoing_link_list:
                    # if link.link_type in ['dr','ur']:
                        # for l in param.level_comosition:
                            # num+=self.z_variable[link.link_seq_no,l].x
                            
                # print(self.b_variable[w,s,t].x,num)
                
                # num=0
                # for link in network.node_list[node_seq].outgoing_link_list:
                    # if link.link_type in ['dr','ur']:
                        # for l in param.level_comosition:
                            # num+=z_variable[link.link_seq_no,l].x
                # print(b_variable[w,s,t].x,num)
                # input()
                
        # Output().output_result(self.__pre_master_model,"G_M1")
        # input()
        
    def __master_pro(self):
 
        self.obj_train=self.__master_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_train')
        
        x=gb.tupledict()
        for a in network.link_list:
            #train-related varibles
            if a.link_type not in ['vp','vv']:
                x[a.link_seq_no]=self.__master_model.addVar(lb=0,ub=a.link_cap,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
                if a.link_type in ['ur','dr','cod','ucd']:        
                    if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                        x[a.link_seq_no].ub=0
                    
                    for l in param.level_comosition:
                        self.z_variable[a.link_seq_no,l]=self.__master_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        # self.z_variable[a.link_seq_no,l].lb = round(object_INI.z_v[a.link_seq_no,l])
                        # self.z_variable[a.link_seq_no,l].ub = round(object_INI.z_v[a.link_seq_no,l])
                        if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                            self.z_variable[a.link_seq_no,l].ub=0


        # for t in range(param.max_time-param.couple_time,param.max_time):
        
        for run_dir in [1,2]:
            # for s in network.turnback_station_list:
            for s in range(param.num_station):
                # if s not in [0,param.num_station-1]:
                    for t in range(param.train_latest_time[run_dir,s]+1,param.max_time):
                        for v_type in [1,2,3]:
                            index=(s,t,run_dir,2)
                            if index in network.node_index_to_no_dict.keys():
                                node_seq=network.node_index_to_no_dict[index]
                                for link in network.node_list[node_seq].incoming_link_list:
                                    if link.link_type in ['dr','ur']:
                                        x[link.link_seq_no].ub=0
            
        for w in demand.OD_list:
            self.waiting_time[w]=self.__master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='waiting_time[%d,%d]'%(w[0],w[1]))
            self.vitual_time[w]=self.__master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='vitual_time[%d,%d]'%(w[0],w[1]))
        
            self.obj_theta[w]=self.__master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_theta[%d,%d]'%(w[0],w[1]))
            step=1 if w[0]<w[1] else -1
            for s in range(w[0],w[1],step):        
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                    self.b_variable[w,s,t]=self.__master_model.addVar(lb=0,ub=min(demand.demand_OD[w],2*param.single_cap),vtype=gb.GRB.CONTINUOUS,name='b[%d,%d,%d,%d]'%(w[0],w[1],s,t))

        #add constraints
        #train flow balance-starting outgoing
        node_seq_no=network.node_index_to_no_dict[(-1,-1,-1,-1)]
        self.__master_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list) == param.max_unit,name="MC1[-1]")
        
        #train flow balance-ending ingoing
        node_seq_no=network.node_index_to_no_dict[(-2,-2,-2,-2)]
        self.__master_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list) == param.max_unit,name="MC1[-2]")
        
        #train flow balance-inter node
        num=0
        for v in network.node_list:
            # print(v.node_id)
            if v.node_id>=0:
                self.__master_model.addConstr((gb.quicksum(x[a.link_seq_no] for a in v.outgoing_link_list if a.link_type not in ['vv','vp'])
                -gb.quicksum(x[a.link_seq_no] for a in v.incoming_link_list if a.link_type not in ['vv','vp']))
                == 0,name="MC1[%d]"%(num))                
                num+=1
        
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction      
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        # tpp=tp+sec.run_time
                        if tp<param.train_latest_time[run_dir,from_node_id]+1:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                
                if len(temp_safe_node)>0:
                    self.__master_model.addConstr((gb.quicksum(self.z_variable[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            <= 1,name="MC2[%d,%d,%d]"%(from_node_id,t,run_dir))
                                
                if len(temp_safe_node_max)>0:
                    self.__master_model.addConstr((gb.quicksum(self.z_variable[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node_max
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            >= 1,name="MC21[%d,%d,%d]"%(from_node_id,t,run_dir))          
                  

                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                
                self.__master_model.addConstr(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                       if link.link_type in ['ur','dr']
                                                       for l in param.level_comosition) <= 1,name="MC4[%d,%d,%d]"%(from_node_id,run_dir,t))
                
                
                self.__master_model.addConstr(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1,name="MC41[%d,%d,%d]"%(from_node_id,run_dir,t))
            
            for link_seq_no in (network.station_arc_run[from_node_id,run_dir] + network.uncouple_arc[from_node_id,run_dir] + network.couple_arc[from_node_id,run_dir]):
                self.__master_model.addConstr(gb.quicksum(l*self.z_variable[link_seq_no,l] for l in param.level_comosition) == x[link_seq_no],name="MC3[%d]"%(link_seq_no))             
            
            
            # self.__master_model.addConstr(gb.quicksum(self.z_variable[link_seq_no,l] for link_seq_no in network.station_arc_run[from_node_id,run_dir] for l in param.level_comosition) == 14)             
            
        
        for a in network.link_list:
            if a.link_type=='vt':
                link_seq_no=a.link_seq_no
                from_node_id=a.from_node_id
                to_node_id=a.to_node_id
                run_dir=a.link_direction
                if a.from_node_id<0:
                    self.__master_model.addConstr(x[link_seq_no] == network.init_unit[run_dir,to_node_id],name="MC5[%d]"%(link_seq_no))             
                else:
                    self.__master_model.addConstr(x[link_seq_no] >= network.end_unit[run_dir,from_node_id],name="MC5[%d]"%(link_seq_no))             
            
            elif a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no 
                self.__master_model.addConstr(x[link_seq_no] >=
                gb.quicksum(x[temp_link.link_seq_no]+0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no))
            
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                self.__master_model.addConstr(x[link_seq_no] <=
                gb.quicksum(x[temp_link.link_seq_no]-0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no)) 
        
        #passenger constraints    
        for w in demand.OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2        
            #cumulative constraints
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                self.__master_model.addConstr(gb.quicksum(self.b_variable[w,s,tp] for tp in range(t+1)
                            if param.earliest_time[w,s]<=tp<=param.latest_time[w,s])
                            <= demand.demand_accum[w,t],name="MC7[%d,%d,%d]"%(w[0],w[1],t))
                
                # index=(s,t,run_dir,1)
                # node_seq_no=network.node_index_to_no_dict[index]
        
        #passenger capacity
        for sec in network.section_list:
            s=sec.from_node_id
            run_dir=sec.run_direction
            to_node=sec.to_node_id
            
            for t in range(param.train_early_time[run_dir,s],param.train_latest_time[run_dir,s]+1): 
                node_index=(s,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                self.__master_model.addConstr(gb.quicksum(self.b_variable[w,s,t] for w in sec.belong_OD_list
                    if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                    <= gb.quicksum(x[link.link_seq_no]*param.single_cap
                        for link in network.node_list[node_seq_no].outgoing_link_list
                        if link.link_type in ['ur','dr']),name="MC8[%d,%d,%d,%d]"%(s,run_dir,t,1))
        
                # temp_link_list=[]
                # for link in network.node_list[node_seq_no].incoming_link_list:                    
                    # if link.link_type in ['ur','dr']:
                        # temp_link_list.append(link.link_seq_no)
                    # elif link.link_type in ['cod','ucd']:
                        # from_node_seq_no=link.from_node_seq_no
                        # for temp_link in network.node_list[from_node_seq_no].incoming_link_list:
                            # if temp_link.link_type in ['ur','dr']:
                                # temp_link_list.append(temp_link.link_seq_no)
                        
                # if len(temp_link_list)>0:
                    # self.__master_model.addConstr(gb.quicksum(self.b_variable[w,s,t] for w in sec.belong_OD_list
                        # if w[0]!=s
                        # if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                        # <= (gb.quicksum(self.z_variable[link_seq_no,l]*l*param.single_cap
                                            # for link_seq_no in temp_link_list
                                                # for l in param.level_comosition)
                                                # )
                            # ,name="MC8[%d,%d,%d,%d]"%(s,run_dir,t,2))
                
                
                
                # temp_link=[]
                # for tp in [t+1]:
                    # if param.train_early_time[run_dir,s]<=tp<=param.train_latest_time[run_dir,s]:
                        # index=(s,tp,run_dir,1)
                        # node_seq=network.node_index_to_no_dict[index]
                        # for link in network.node_list[node_seq].outgoing_link_list:
                            # if link.link_type in ['ur','dr']:
                                # temp_link.append(link.link_seq_no)
                
                
                # temp_link1=[]
                # for tp in [t-1]:
                    # if param.train_early_time[run_dir,s]<=tp<=param.train_latest_time[run_dir,s]:
                        # index=(s,tp,run_dir,1)
                        # node_seq=network.node_index_to_no_dict[index]
                        # for link in network.node_list[node_seq].outgoing_link_list:
                            # if link.link_type in ['ur','dr']:
                                # temp_link1.append(link.link_seq_no)
                
                # # print(len(temp_link))
                # # input()
                
                # self.__master_model.addConstr(gb.quicksum(self.b_variable[w,s,t] for w in sec.belong_OD_list if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                # <= (1-gb.quicksum(self.z_variable[link_seq_no,l] for link_seq_no in temp_link for l in param.level_comosition))*1800
                # )
                
                # # for w in demand.OD_list:
                # for w in param.key_OD_list:
                    # if w in sec.belong_OD_list and param.earliest_time[w,s]<=t<=param.latest_time[w,s]:
                        # self.__master_model.addConstr(self.b_variable[w,s,t]<=
                            # (1-gb.quicksum(self.z_variable[link_seq_no,l] for link_seq_no in temp_link for l in param.level_comosition))*demand.demand_max[w]
                            # )
                            
                    # if w in sec.belong_OD_list and param.earliest_time[w,s]<=t<=param.latest_time[w,s]:
                        # self.__master_model.addConstr(self.b_variable[w,s,t]<=
                            # (1-gb.quicksum(self.z_variable[link_seq_no,l] for link_seq_no in temp_link1 for l in param.level_comosition))*demand.demand_max[w]
                            # )


        # for w in demand.OD_list:
        for w in param.key_OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2
            step=1 if s<sp else -1
            
            #passenger flow balance-inter
            for v in network.node_list:
                if v.node_attr==1 and v.node_direction==run_dir and (s<v.node_id<sp or sp<v.node_id<s):
                    ts=v.node_id
                    tt=v.node_time
                    
                    
                    if param.earliest_time[w,ts]<=tt<=param.latest_time[w,ts]:
                        temp_link_list=[]
                        temp_node={}
                        for link in v.incoming_link_list:
                            if link.link_type in ['dr','ur','ucd']:
                                temp_link_list.append(link)
                                if link.link_type in ['dr','ur']:
                                    temp_node[link.link_seq_no]=link.from_node_seq_no
                                else:
                                    for t_link in network.node_list[link.from_node_seq_no].incoming_link_list:
                                        if t_link.link_type in ['dr','ur']:
                                            temp_node[link.link_seq_no]=t_link.from_node_seq_no
                            elif link.link_type in ['cod']:
                                from_seq_no=link.from_node_seq_no
                                for t_link in network.node_list[from_seq_no].incoming_link_list:
                                    if t_link.link_type in ['dr','ur']:
                                        temp_link_list.append(t_link)
                                        temp_node[t_link.link_seq_no]=t_link.from_node_seq_no
                        
                        #new constraint
                        if len(temp_link_list)>0:                          
                            for temp_link in temp_link_list:
                                pre_s=None
                                pre_t=None
                                if temp_link.link_type=='ucd':
                                    for t_link in network.node_list[temp_link.from_node_seq_no].incoming_link_list:
                                        if t_link.link_type in ['dr','ur']:
                                            from_node=t_link.from_node_seq_no
                                            pre_s=network.node_list[from_node].node_id
                                            pre_t=network.node_list[from_node].node_time
                                else:
                                    from_node=temp_link.from_node_seq_no
                                    pre_s=network.node_list[from_node].node_id
                                    pre_t=network.node_list[from_node].node_time
                                
                                if pre_s!=None and pre_t!=None:
                                    if param.earliest_time[w,pre_s]<=pre_t<=param.latest_time[w,pre_s]:
                                        self.__master_model.addConstr(self.b_variable[w,ts,tt]>=
                                            (gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition)-1)*(demand.demand_OD[w]+1)+self.b_variable[w,pre_s,pre_t]
                                            ,name="MC611[%d]"%(temp_link.link_seq_no))
                                            
                                        # # self.__master_model.addConstr(self.b_variable[w,ts,tt]<=
                                            # # (1-gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition))*(demand.demand_OD[w]+1)+self.b_variable[w,pre_s,pre_t]
                                            # # ,name="MC612[%d]"%(temp_link.link_seq_no))
                                            
                            # # self.__master_model.addConstr(self.b_variable[w,ts,tt] ==
                            # # (gb.quicksum(gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition)*self.b_variable[w,network.node_list[temp_node[temp_link.link_seq_no]].node_id,network.node_list[temp_node[temp_link.link_seq_no]].node_time]
                                    # # for temp_link in temp_link_list                                    
                                    # # if param.earliest_time[w,network.node_list[temp_link.from_node_seq_no].node_id]<=network.node_list[temp_link.from_node_seq_no].node_time<=param.latest_time[w,network.node_list[temp_link.from_node_seq_no].node_id]))                            
                            # # ,name="MC612[%d,%d,%d,%d]"%(w[0],w[1],ts,tt))
                            
                
            for sb in range(s,sp-step,step):
                for t in range(param.earliest_time[w,sb],param.latest_time[w,sb]+1):
                    index=(sb,t,run_dir,1)
                    node_seq=network.node_index_to_no_dict[index]
                    temp_node_list=[]
                    temp_link_list=[]
                    for link in network.node_list[node_seq].outgoing_link_list:
                        if link.link_type in ['ur','dr']:
                            to_seq_no=link.to_node_seq_no
                            index=network.node_no_dict_to_index[to_seq_no]
                            tsp=index[0]
                            ttp=index[1]
                            if index[3]==1 and param.earliest_time[w,tsp]<=ttp<=param.latest_time[w,tsp]:
                                if to_seq_no not in temp_node_list:
                                    temp_node_list.append(to_seq_no)
                                
                                temp_link_list.append(link.link_seq_no)
                                
                            elif index[3]==2 and param.earliest_time[w,tsp]<=ttp+param.couple_time<=param.latest_time[w,tsp]:
                                for t_link in network.node_list[to_seq_no].outgoing_link_list:
                                    if t_link.link_type in ['cod']:
                                        if t_link.to_node_seq_no not in temp_node_list:
                                            temp_node_list.append(t_link.to_node_seq_no)
                                
                                temp_link_list.append(link.link_seq_no)
                                
                            elif index[3]==3 and param.earliest_time[w,tsp]<=ttp+param.uncouple_time<=param.latest_time[w,tsp]:
                                for t_link in network.node_list[to_seq_no].outgoing_link_list:
                                    if t_link.link_type in ['ucd']:
                                        if t_link.to_node_seq_no not in temp_node_list:
                                            temp_node_list.append(t_link.to_node_seq_no)
                                        
                                        temp_link_list.append(t_link.link_seq_no)

                    # self.__master_model.addConstr(self.b_variable[w,sb,t] <=
                        # (gb.quicksum(self.z_variable[t_link.link_seq_no,l]
                         # for t_node in temp_node_list
                         # for t_link in network.node_list[t_node].outgoing_link_list
                         # if t_link.link_type in ['ur','dr']
                         # for l in param.level_comosition)*(demand.demand_OD[w]))
                        # ,name="MC613[%d,%d,%d,%d]"%(w[0],w[1],sb,t))
                        # 上面约束没用
                        
                    self.__master_model.addConstr(self.b_variable[w,sb,t] <=
                        (gb.quicksum(self.z_variable[t_link_seq,l]
                         for t_link_seq in temp_link_list                         
                         for l in param.level_comosition)*(2*demand.demand_max[w]))
                        ,name="MC614[%d,%d,%d,%d]"%(w[0],w[1],sb,t))
                            
        # #valid inequality
        # self.__master_model.addConstr(param.weight_train*self.obj_train+gb.quicksum(self.obj_theta[w] for w in demand.OD_list)
                            # >=object_INI.estimate_lower_bound,name="vInEq1")#object_INI.estimate_lower_bound 这个不等式没用
        
        # self.__master_model.addConstr(param.weight_train*self.obj_train+gb.quicksum(self.obj_theta[w] for w in demand.OD_list)
                    # <=object_BAC.UB,name="vInEq2")#这个不等式稍微有用，可以根据启发式上界动态利用czlay进行求解
        
        # for sec in network.section_list:
            # run_dir=sec.run_direction
            # s=sec.from_node_id
            
            # self.__master_model.addConstr(param.weight_train*(
            # gb.quicksum(sec.sec_dis*self.z_variable[link_no,l]*param.cost_composition[l]                                                   
                                    # for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                    # for l in param.level_comosition))
            
            # # +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]
                # # for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir]))))
            
            # +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(self.b_variable[w,w[0],tp] for tp in range(param.earliest_time[w,w[0]],t+1)))
                                                                # for w in sec.belong_OD_list if w[0]==s
                                                                # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
            # +param.weight_pax*param.vitual_pax_cost*1*gb.quicksum((demand.demand_OD[w]-gb.quicksum(self.b_variable[w,w[0],t] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)))for w in sec.belong_OD_list if w[0]==s)
            # >=object_INI.sec_estimate_lower_bound[sec.section_id],name="MC9[%d,%d]"%(s,run_dir))
            
            # unit_time=30
            # sta_time=0
            # end_time=0
            # for pt in range(object_INI.max_period[sec.section_id]):
                # if pt==object_INI.max_period[sec.section_id]-1:
                    # sta_time=pt*unit_time
                    # end_time=param.train_latest_time[run_dir,s]+1
                    
                    # self.__master_model.addConstr(param.weight_train*(
                        # gb.quicksum(sec.sec_dis*self.z_variable[link_no,l]*param.cost_composition[l]                                                   
                                                # for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                # if sta_time<=network.link_list[link_no].start_time<end_time
                                                # for l in param.level_comosition))
                        # +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(self.b_variable[w,w[0],tp] for tp in range(sta_time,t+1) if param.earliest_time[w,s]<=tp<=param.latest_time[w,s]))
                                                                            # for w in sec.belong_OD_list if w[0]==s
                                                                            # for t in range(sta_time,end_time)
                                                                            # if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                        
                        # +param.weight_pax*param.vitual_pax_cost*gb.quicksum((demand.demand_OD[w]-gb.quicksum(self.b_variable[w,w[0],t] for t in range(sta_time,end_time)
                                                                # if param.earliest_time[w,s]<=t<=param.latest_time[w,s]))
                                                                # for w in sec.belong_OD_list if w[0]==s)
                        
                        # >=object_INI.lower_bound_period[sec.section_id,pt],name="MC9[%d,%d,%d]"%(s,run_dir,pt))
                

                
                
                # else:
                    # sta_time=pt*unit_time
                    # end_time=(pt+1)*unit_time
                    
                    # self.__master_model.addConstr(param.weight_train*(
                        # gb.quicksum(sec.sec_dis*self.z_variable[link_no,l]*param.cost_composition[l]                                                   
                                                # for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                # if sta_time<=network.link_list[link_no].start_time<end_time
                                                # for l in param.level_comosition))
                        # +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(self.b_variable[w,w[0],tp] for tp in range(sta_time,t+1) if param.earliest_time[w,s]<=tp<=param.latest_time[w,s]))
                                                                            # for w in sec.belong_OD_list if w[0]==s
                                                                            # for t in range(sta_time,end_time)
                                                                            # if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                        
                        # +param.weight_pax*1*gb.quicksum((demand.demand_OD[w]-gb.quicksum(self.b_variable[w,w[0],t] for t in range(sta_time,end_time)
                                                                # if param.earliest_time[w,s]<=t<=param.latest_time[w,s]))
                                                                # for w in sec.belong_OD_list if w[0]==s)
                        
                        # >=object_INI.lower_bound_period[sec.section_id,pt],name="MC9[%d,%d,%d]"%(s,run_dir,pt))
                
            
            # print(sec.section_id,object_INI.sec_estimate_lower_bound[sec.section_id])
            # input()
       
        # # #valid inequality
        # for w in demand.OD_list:
            # self.__master_model.addConstr(self.waiting_time[w] == gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(self.b_variable[w,w[0],tp] for tp in range(param.earliest_time[w,w[0]],t+1)))
                                            # for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1)
                                            # )*param.wait_pax_cost,name="waiting_time[%d,%d]"%(w[0],w[1]))
            # self.__master_model.addConstr(self.vitual_time[w] == param.vitual_pax_cost*((demand.demand_OD[w]-gb.quicksum(self.b_variable[w,w[0],t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1)))
                                                                    # )
                                         # ,name="vitual_timeMC9[%d,%d]"%(w[0],w[1]))
        
            # self.__master_model.addConstr(self.obj_theta[w] >= param.weight_pax*(self.waiting_time[w]+self.vitual_time[w]),name="MCB[%d,%d]"%(w[0],w[1]))             
            # #上面约束没用

        #objective function
        self.__master_model.addConstr(gb.quicksum(sec.sec_dis*self.z_variable[link_no,l]*param.cost_composition[l] 
                                                    for sec in network.section_list
                                                        for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                            for l in param.level_comosition)
                                    +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]                                    
                                    for s in range(param.num_station)
                                        for run_dir in [1,2]
                                            for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir])))
                                    == self.obj_train,name="MCA")

        
        self.__master_model.setObjective(param.weight_train*self.obj_train+gb.quicksum(self.obj_theta[w] for w in demand.OD_list),gb.GRB.MINIMIZE)
        
        
        for key in object_INI.last_link:
            if key in self.z_variable.keys():
                self.z_variable[key].ub=0
        
        
        # self.__master_model.params.outputflag = 0
        # self.__master_model.Params.MIPGap=0.001
        # self.__master_model.params.FeasibilityTol=0.0001
        
        # for key in self.z_variable.keys():
            # self.z_variable[key].start = object_INI.ini_z_v[key] 
            
        # for key in self.b_variable.keys():
            # self.b_variable[key].start = object_INI.ini_b_v[key]
            
            
            
    
    def dual_sub_pro(self,w):
        self.obj_dual[w]=self.dual_sub_model[w].addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_pax')

        #defined variables
        dual_pi=gb.tupledict()
        s_ori=w[0]
        s_des=w[1]
        step=1 if s_ori<s_des else -1
        run_dir=1 if s_ori<s_des else 2
        
        for s in range(s_ori,s_des+step,step):
            for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                for v_type in [1,2,3]:
                    index=(s,t,run_dir,v_type)
                    if index in network.node_index_to_no_dict.keys():                            
                        node_seq_no=network.node_index_to_no_dict[index] 
                        dual_pi[w,node_seq_no]=self.dual_sub_model[w].addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='dual_pi[%d,%d,%d]'%(w[0],w[1],node_seq_no))
                        if v_type==1 and s!=w[1]:
                            self.dual_lambda[w,s,t]=self.dual_sub_model[w].addVar(lb=-gb.GRB.INFINITY,ub=0,vtype=gb.GRB.CONTINUOUS,name='dual_lambda[%d,%d,%d,%d]'%(w[0],w[1],s,t))
                            # print(w,s,t)
                            # input()
                            
            if s==s_ori or s==s_des:
                index=(-100-s,-100-s,-100-s,-100-s)
                node_seq_no=network.node_index_to_no_dict[index]
                dual_pi[w,node_seq_no]=self.dual_sub_model[w].addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='dual_pi[%d,%d,%d]'%(w[0],w[1],node_seq_no))
                self.dual_pi_OD[w,node_seq_no]=dual_pi[w,node_seq_no]
                self.OD_node[s]=node_seq_no
           
        #defined constraints
        for a in network.link_list:
            if a.link_type in ['ucd','cod','ur','dr']:
                if w[0]<=a.from_node_id<=a.to_node_id<=w[1] or w[1]<=a.to_node_id<=a.from_node_id<=w[0]:
                    if param.earliest_time[w,a.to_node_id]<=a.end_time<=param.latest_time[w,a.to_node_id]:
                        if a.from_node_id==w[0] and a.link_type in ['ur','dr']:
                            self.dual_gamma[w,a.link_seq_no]=self.dual_sub_model[w].addVar(lb=-gb.GRB.INFINITY,ub=0,vtype=gb.GRB.CONTINUOUS,name='dual_gamma[%d]'%(a.link_seq_no))
                    
                        elif a.to_node_id==w[1]:
                            self.dual_gamma[w,a.link_seq_no]=self.dual_sub_model[w].addVar(lb=-gb.GRB.INFINITY,ub=0,vtype=gb.GRB.CONTINUOUS,name='dual_gamma[%d]'%(a.link_seq_no))
                            
                        elif w[1]<a.to_node_id<=a.from_node_id<w[0] or w[0]<a.from_node_id<=a.to_node_id<w[1]:
                            self.dual_gamma[w,a.link_seq_no]=self.dual_sub_model[w].addVar(lb=-gb.GRB.INFINITY,ub=0,vtype=gb.GRB.CONTINUOUS,name='dual_gamma[%d]'%(a.link_seq_no))
                
            #pax-related varibles
            if a.link_type not in ['vt','tud','tdu','idl','ucr']:  
                from_node_seq_no=a.from_node_seq_no
                to_node_seq_no=a.to_node_seq_no
                
            
                flag1=0;flag2=0
                run_dir=1 if w[0]<w[1] else 2
                
                if a.from_node_id>=0 and (w[1]<=a.from_node_id<=w[0] or w[0]<=a.from_node_id<=w[1]) and (param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]):
                    flag1=1
                elif a.from_node_id<0:
                    flag1=1
                if  a.to_node_id>=0 and (w[1]<=a.to_node_id<=w[0] or w[0]<=a.to_node_id<=w[1]) and (param.earliest_time[w,a.to_node_id]<=a.end_time<=param.latest_time[w,a.to_node_id]):
                    flag2=1
                elif a.to_node_id<0:
                    flag2=1
                
                if a.link_type=='vv':
                    flag1=1
                    flag2=1
                
                if (flag1==1) and (flag2==1):                   
                    if a.link_type=='vv' and a.from_node_id==w[0] and a.to_node_id==w[1]:                    
                        self.dual_sub_model[w].addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no] <= param.weight_pax*param.vitual_pax_cost,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                        
                    elif a.link_type=='vp' and (a.from_node_id==w[1] or a.to_node_id==w[0]) and a.link_direction==run_dir:
                        self.dual_sub_model[w].addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no] <= 0,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                        
                    elif a.link_type not in ['vv','vp'] and a.link_direction==run_dir:
                        if (w[0]<=a.from_node_id<=a.to_node_id<=w[1] or w[1]<=a.to_node_id<=a.from_node_id<=w[0]) and param.earliest_time[w,a.to_node_id]<=a.end_time<=param.latest_time[w,a.to_node_id]:
                            index=network.node_no_dict_to_index[from_node_seq_no]
                            temp_s=index[0]
                            temp_t=index[1]
                            temp_r=index[2]
                            if a.link_type in ['ur','dr'] and a.from_node_id!=w[1]:                            
                                if a.from_node_id==w[0]:
                                    # print(w,temp_t,param.latest_time[w,temp_s]-temp_t)
                                    # input()
                                    self.dual_sub_model[w].addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no]+self.dual_lambda[w,temp_s,temp_t]+self.dual_gamma[w,a.link_seq_no] <= -param.weight_pax*param.wait_pax_cost*1*(param.latest_time[w,temp_s]-temp_t+1),name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                                else:
                                    self.dual_sub_model[w].addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no]+self.dual_lambda[w,temp_s,temp_t]+self.dual_gamma[w,a.link_seq_no] <= 0,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                              
                                    # print(w,a.from_node_id,a.to_node_id,"test...")
                                    # input()
                            if a.link_type in ['ucd','cod'] and a.from_node_id!=w[0]:
                                self.dual_sub_model[w].addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no]+self.dual_gamma[w,a.link_seq_no] <= 0,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
    
        self.dual_sub_model[w].addConstr(0 == self.obj_dual[w], name='MC3')
        
        self.dual_sub_model[w].setObjective(self.obj_dual[w],gb.GRB.MAXIMIZE)
        self.dual_sub_model[w].update()
        self.dual_sub_model[w].params.outputflag = 0
        self.dual_sub_model[w].params.InfUnbdInfo = 1


    def dual_sub_pro_one(self):
        self.obj_dual_n=self.dual_sub_model_n.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_pax')

        #defined variables
        dual_pi=gb.tupledict()
        for w in demand.OD_list:
            s_ori=w[0]
            s_des=w[1]
            step=1 if s_ori<s_des else -1
            run_dir=1 if s_ori<s_des else 2
            
            for s in range(s_ori,s_des+step,step):
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                    for v_type in [1,2,3]:
                        index=(s,t,run_dir,v_type)
                        if index in network.node_index_to_no_dict.keys():                            
                            node_seq_no=network.node_index_to_no_dict[index] 
                            dual_pi[w,node_seq_no]=self.dual_sub_model_n.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='dual_pi[%d,%d,%d]'%(w[0],w[1],node_seq_no))
                            if v_type==1 and s==w[0]:
                                self.dual_lambda_n[w,t]=self.dual_sub_model_n.addVar(lb=-gb.GRB.INFINITY,ub=0,vtype=gb.GRB.CONTINUOUS,name='dual_lambda[%d,%d,%d]'%(w[0],w[1],node_seq_no))
                
                if s==s_ori or s==s_des:
                    index=(-100-s,-100-s,-100-s,-100-s)
                    node_seq_no=network.node_index_to_no_dict[index]
                    dual_pi[w,node_seq_no]=self.dual_sub_model_n.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='dual_pi[%d,%d,%d]'%(w[0],w[1],node_seq_no))
                    self.dual_pi_OD_n[w,node_seq_no]=dual_pi[w,node_seq_no]
                    self.OD_node_n[s]=node_seq_no
           
        #defined constraints
        for a in network.link_list:
            
            if a.link_type in ['ucd','cod','ur','dr']:
                self.dual_gamma_n[a.link_seq_no]=self.dual_sub_model_n.addVar(lb=-gb.GRB.INFINITY,ub=0,vtype=gb.GRB.CONTINUOUS,name='dual_gamma[%d]'%(a.link_seq_no))
            
            #pax-related varibles
            if a.link_type not in ['vt','tud','tdu','idl','ucr']:  
                from_node_seq_no=a.from_node_seq_no
                to_node_seq_no=a.to_node_seq_no
                
                for w in demand.OD_list:
                    flag1=0;flag2=0
                    run_dir=1 if w[0]<w[1] else 2
                    
                    if a.from_node_id>=0 and (w[1]<=a.from_node_id<=w[0] or w[0]<=a.from_node_id<=w[1]) and (param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]):
                        flag1=1
                    elif a.from_node_id<0:
                        flag1=1
                    if  a.to_node_id>=0 and (w[1]<=a.to_node_id<=w[0] or w[0]<=a.to_node_id<=w[1]) and (param.earliest_time[w,a.to_node_id]<=a.end_time<=param.latest_time[w,a.to_node_id]):
                        flag2=1
                    elif a.to_node_id<0:
                        flag2=1
                    
                    if a.link_type=='vv':
                        flag1=1
                        flag2=1
                    
                    if (flag1==1) and (flag2==1):                   
                        if a.link_type=='vv' and a.from_node_id==w[0] and a.to_node_id==w[1]:                    
                            self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no] <= param.weight_pax*param.vitual_pax_cost,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                            
                        elif a.link_type=='vp' and (a.from_node_id==w[1] or a.to_node_id==w[0]) and a.link_direction==run_dir:
                            self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no] <= 0,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                            
                        elif a.link_type not in ['vv','vp'] and a.link_direction==run_dir:
                            if (w[0]<=a.from_node_id<=a.to_node_id<=w[1] or w[1]<=a.to_node_id<=a.from_node_id<=w[0]) and param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]:
                                if a.link_type in ['ur','dr']:
                                    index=network.node_no_dict_to_index[from_node_seq_no]
                                    temp_s=index[0]
                                    temp_t=index[1]
                                    temp_r=index[2]
                                    if a.from_node_id==w[0]:
                                        # print(w,temp_t,param.latest_time[w,temp_s]-temp_t)
                                        # input()
                                        self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no]+self.dual_lambda_n[w,temp_t]+self.dual_gamma_n[a.link_seq_no] <= -param.weight_pax*param.wait_pax_cost*1*(param.latest_time[w,temp_s]-temp_t+1),name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                                    else:
                                        self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no]+self.dual_gamma_n[a.link_seq_no] <= 0,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                                        # print(w,a.from_node_id,a.to_node_id,"test...")
                                        # input()
                                if a.link_type in ['ucd','cod']:
                                    self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no]+self.dual_gamma_n[a.link_seq_no] <= 0,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
        
        self.dual_sub_model_n.addConstr(0 == self.obj_dual_n, name='MC3')
        
        self.dual_sub_model_n.setObjective(self.obj_dual_n,gb.GRB.MAXIMIZE)
        self.dual_sub_model_n.update()
        self.dual_sub_model_n.params.outputflag = 0
        self.dual_sub_model_n.params.InfUnbdInfo = 1



    def update_sub_model_benders(self,w):
                
        # print(len(self.dual_sub_model.getConstrs())-1)
        self.dual_sub_model.remove(self.dual_sub_model.getConstrs()[len(self.dual_sub_model.getConstrs())-1])
        # print(self.dual_pi_OD[w,self.OD_node[w[0]]])
        # input()
        self.dual_sub_model.addConstr((self.dual_pi_OD[w,self.OD_node[w[0]]]*demand.demand_OD[w]
                                                    -self.dual_pi_OD[w,self.OD_node[w[1]]]*demand.demand_OD[w]
                                                    +gb.quicksum(self.dual_lambda[w,s,t]*max(0,self.b_variable[w,t].x)                                                        
                                                        for s in network.OD_station[w]
                                                        if s!=w[1]
                                                        for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)) 
                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            )
                            +gb.quicksum(self.dual_gamma[w,link_seq_no]*param.single_cap*gb.quicksum(max(self.z_variable[link_seq_no,l].x,0)*l for l in param.level_comosition)
                                for link_seq_no in [key for key in self.dual_gamma.keys() if key[0] == w])
                            ==self.obj_dual[w], name='MC3')
        
        
        self.dual_sub_model[w].update()
        
    def update_sub_model(self,w,b_var,z_var):
        # print(len(self.dual_sub_model[w].getConstrs())-1)
        self.dual_sub_model[w].remove(self.dual_sub_model[w].getConstrs()[len(self.dual_sub_model[w].getConstrs())-1])
        # print(self.dual_pi_OD[w,self.OD_node[w[0]]])
        # input()
        self.dual_sub_model[w].addConstr((self.dual_pi_OD[w,self.OD_node[w[0]]]*demand.demand_OD[w]
                                                    -self.dual_pi_OD[w,self.OD_node[w[1]]]*demand.demand_OD[w]
                                                    +gb.quicksum(self.dual_lambda[w,s,t]*max(0,b_var[w,s,t])                                       
                                                        for s in network.OD_station[w]
                                                        if s!=w[1]
                                                        for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            )
                            +gb.quicksum(self.dual_gamma[link_seq_no]*param.single_cap*gb.quicksum(max(z_var[link_seq_no[1],l],0)*l for l in param.level_comosition)
                               for link_seq_no in [key for key in self.dual_gamma.keys() if key[0] == w])
                            ==self.obj_dual[w], name='MC3')
        
        
        self.dual_sub_model[w].update()
        
        # self.dual_sub_model.write("xxx33.lp")
        # input()

        # self.dual_sub_model.optimize()
        # if object_BAC.dual_sub_model.status != gb.GRB.OPTIMAL:
            # self.dual_sub_model.computeIIS()
            # self.dual_sub_model.write("xxx33.ilp")
            # input()

    def update_sub_model_one(self,b_var,z_var):
        # print(len(self.dual_sub_model[w].getConstrs())-1)
        self.dual_sub_model_n.remove(self.dual_sub_model_n.getConstrs()[len(self.dual_sub_model_n.getConstrs())-1])
        # print(self.dual_pi_OD[w,self.OD_node[w[0]]])
        # input()
        self.dual_sub_model_n.addConstr(gb.quicksum((self.dual_pi_OD_n[w,self.OD_node_n[w[0]]]*demand.demand_OD[w]
                                                    -self.dual_pi_OD_n[w,self.OD_node_n[w[1]]]*demand.demand_OD[w]
                                                    +gb.quicksum(self.dual_lambda_n[w,t]*max(0,b_var[w,w[0],t])                                                        
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            ) for w in demand.OD_list)
                            
                            +gb.quicksum(self.dual_gamma_n[link_seq_no]*param.single_cap*gb.quicksum(max(z_var[link_seq_no,l],0)*l for l in param.level_comosition)
                                for sec in network.section_list
                                for link_seq_no in (network.station_arc_run[sec.from_node_id,sec.run_direction] + network.uncouple_arc[sec.from_node_id,sec.run_direction] + network.couple_arc[sec.from_node_id,sec.run_direction])
                                )
                            ==self.obj_dual_n)
        
        
        self.dual_sub_model_n.update()


    def __update_feasible_link(self,flag,feasible_link,time_gap):        
        num_arc=0
        if flag==0:#==0表示将feasible_link中弧段的上界置为1
            for link_seq_no in feasible_link:                
                
                if num_arc>900:
                    break
                
                a=network.link_list[link_seq_no]
                if a.link_type in ['ur','dr']:  
                    s=a.from_node_id
                    sp=a.to_node_id
                    run_dir=a.link_direction
                    from_time=a.start_time
                    run_time=a.end_time-a.start_time
                    for t in range(max(from_time-time_gap,param.train_early_time[run_dir,s]),min(from_time+time_gap,param.train_latest_time[run_dir,s])+1):
                        from_index=(s,t,run_dir,1)
                        tp=t+run_time
                        if tp<=param.train_latest_time[run_dir,sp]:
                            for v_type in [1,2,3]:
                                to_index=(sp,tp,run_dir,v_type)
                                from_seq=None;to_seq=None
                                if from_index in network.node_index_to_no_dict.keys():
                                    from_seq=network.node_index_to_no_dict[from_index]
                                if to_index in network.node_index_to_no_dict.keys():
                                    to_seq=network.node_index_to_no_dict[to_index]
                                if from_seq!=None and to_seq!=None:
                                    link_index=(from_seq,to_seq)                                
                                    if link_index in network.link_index_to_no_dict.keys():
                                        temp_link_seq_no=network.link_index_to_no_dict[link_index]
                                        for l in param.level_comosition:
                                            # if object_INI.z_v[temp_link_seq_no,l].lb==1:
                                                # print(object_INI.z_v[temp_link_seq_no,l].ub,object_INI.z_v[temp_link_seq_no,l].lb)
                                                # input()
                                            object_INI.z_v[temp_link_seq_no,l].ub=1
                                        
                                        if temp_link_seq_no not in object_INI.feasible_link_for_bestSol:
                                            num_arc+=1
                                        
        elif flag==1:#表示feasible_link中的弧段上界恢复为0
            for link_seq_no in feasible_link:                
                
                if num_arc>900:
                    break
                
                a=network.link_list[link_seq_no]
                if a.link_type in ['ur','dr']:  
                    s=a.from_node_id
                    sp=a.to_node_id
                    run_dir=a.link_direction
                    from_time=a.start_time
                    run_time=a.end_time-a.start_time
                    for t in range(max(from_time-time_gap,param.train_early_time[run_dir,s]),min(from_time+time_gap,param.train_latest_time[run_dir,s])+1):
                        from_index=(s,t,run_dir,1)
                        tp=t+run_time
                        if tp<=param.train_latest_time[run_dir,sp]:
                            for v_type in [1,2,3]:
                                to_index=(sp,tp,run_dir,v_type)
                                from_seq=None;to_seq=None
                                if from_index in network.node_index_to_no_dict.keys():
                                    from_seq=network.node_index_to_no_dict[from_index]
                                if to_index in network.node_index_to_no_dict.keys():
                                    to_seq=network.node_index_to_no_dict[to_index]
                                if from_seq!=None and to_seq!=None:
                                    link_index=(from_seq,to_seq)  
                                    if link_index in network.link_index_to_no_dict.keys():
                                        temp_link_seq_no=network.link_index_to_no_dict[link_index]
                                        for l in param.level_comosition:
                                            object_INI.z_v[temp_link_seq_no,l].ub=0 

                                        if temp_link_seq_no not in object_INI.feasible_link_for_bestSol:
                                            num_arc+=1
                                            
        elif flag==3:#所有格置为0，1
            for key1 in [key for key in object_INI.z_v.keys() if key[1] == param.level_comosition[0]]: 
                link_seq_no=key1[0]              
                a=network.link_list[link_seq_no]
                if a.link_type in ['ur','dr']:  
                    s=a.from_node_id
                    sp=a.to_node_id
                    run_dir=a.link_direction
                    from_time=a.start_time
                    run_time=a.end_time-a.start_time
                    for t in range(max(from_time-time_gap,param.train_early_time[run_dir,s]),min(from_time+time_gap,param.train_latest_time[run_dir,s])+1):
                        from_index=(s,t,run_dir,1)
                        tp=t+run_time
                        if tp<=param.train_latest_time[run_dir,sp]:
                            for v_type in [1,2,3]:
                                to_index=(sp,tp,run_dir,v_type)
                                from_seq=None;to_seq=None
                                if from_index in network.node_index_to_no_dict.keys():
                                    from_seq=network.node_index_to_no_dict[from_index]
                                if to_index in network.node_index_to_no_dict.keys():
                                    to_seq=network.node_index_to_no_dict[to_index]
                                if from_seq!=None and to_seq!=None:
                                    link_index=(from_seq,to_seq)  
                                    if link_index in network.link_index_to_no_dict.keys():
                                        temp_link_seq_no=network.link_index_to_no_dict[link_index]
                                        for l in param.level_comosition:
                                            object_INI.z_v[temp_link_seq_no,l].ub=0
                                            object_INI.z_v[temp_link_seq_no,l].lb=0                                          
        
    def primary_pro_feasibleSol(self,z_var):
        flagture=False
        movestep=5 #移动步长
        localstep=0 #非移动
        b_v={}
        z_v={}
        
        #step 1 筛选了一部分弧段
        feasible_link=[]
        for key in z_var.keys():
            link_seq_no=key[0]
            if network.link_list[link_seq_no].link_type in ['dr','ur']:
                if abs(abs(z_var[key])-0.5)<=0.1:
                    feasible_link.append(link_seq_no)
        
        # print("len:",len(feasible_link))
        # object_INI.second_origin_model.update()
        
        self.__update_feasible_link(0,feasible_link,movestep) #利用筛选的弧段更新模型
        
        object_INI.second_origin_model.update()
        object_INI.second_origin_model.optimize()
        
        # print("generating UB:",self.UB,object_INI.second_origin_model.objVal)
        # input()
        
        # if object_INI.second_origin_model.SolCount>0:  #得到可行解        
        if self.UB>object_INI.second_origin_model.objVal+0.1 and object_INI.second_origin_model.SolCount>0:
                flagture=True
                self.UB=object_INI.second_origin_model.objVal            
                self.best_x_value={} 
                
                b_v = {key: var.X for key, var in object_INI.b_v.items()}
                z_v = {key: var.X for key, var in object_INI.z_v.items()}
                # print("UB1:",self.UB)
                
                # 清空可用弧
                self.__update_feasible_link(3,[],localstep)
                
                object_INI.feasible_link_for_bestSol=[]
                for key in object_INI.z_v.keys():
                    link_seq_no=key[0]
                    if abs(object_INI.z_v[key].x)>0.9:
                        object_INI.feasible_link_for_bestSol.append(link_seq_no)
                        self.best_x_value[key[0]]=round(key[1])
                
                #利用当前最优解更新可行弧
                self.__update_feasible_link(0,object_INI.feasible_link_for_bestSol,localstep)           
        else:
            self.__update_feasible_link(1,feasible_link,movestep)
            self.__update_feasible_link(0,object_INI.feasible_link_for_bestSol,localstep) 
        
        # self.LB=max(self.LB,temp_LB)  
        # gap=100*(self.UB-self.LB)/self.UB    
        # print("UB is {}, LB is {}, gap is {}.".format(self.UB,self.LB,gap))
        # input()
        # if flagture==True:
            # print("self.UB",self.UB)
            # input()
        
        object_INI.second_origin_model.update()
        return flagture,b_v,z_v
        
    
    def update_UB(self,z_var):  
        self.best_x_value={}               
        
        # 清空可用弧
        self.__update_feasible_link(3,[],0)
        
        object_INI.feasible_link_for_bestSol=[]
        for key in object_INI.z_v.keys():
            link_seq_no=key[0]
            if abs(object_INI.z_v[key].x)>0.9:
                object_INI.feasible_link_for_bestSol.append(link_seq_no)
                self.best_x_value[key[0]]=round(key[1])
        
        #利用当前最优解更新可行弧
        self.__update_feasible_link(0,object_INI.feasible_link_for_bestSol,0) 
    
    def add_valid_inequality(self,model,z_var,b_var):        
        # print("adding to inequality!")
        global num_O_cuts
        num=0
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction        
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                temp_value=0
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                        for link in network.node_list[node_seq_no].outgoing_link_list:
                            if link.link_type in ['ur','dr']:
                                for l in param.level_comosition:
                                    temp_value+=z_var[link.link_seq_no,l]
                
                temp_safe_node_max=[]
                temp_max_value=0
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        # tpp=tp+sec.run_time
                        if tp<=param.train_latest_time[run_dir,from_node_id]:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                            for link in network.node_list[node_seq_no].outgoing_link_list:
                                if link.link_type in ['ur','dr']:
                                    for l in param.level_comosition:
                                        temp_max_value+=z_var[link.link_seq_no,l]

                if temp_value>1.1 and len(temp_safe_node)>0:          
                    model.cbLazy((gb.quicksum(self.z_variable[link.link_seq_no,l]
                        for l in param.level_comosition
                          for node_seq_no in temp_safe_node
                            for link in network.node_list[node_seq_no].outgoing_link_list
                              if link.link_type in ['ur','dr']))<=1)
                    num+=1
                    
                if temp_max_value<0.9 and len(temp_safe_node_max)>0:
                    # print(temp_max_value,from_node_id,t,run_dir)
                    # print(temp_safe_node_max)
                    # input()
                    model.cbLazy((gb.quicksum(self.z_variable[link.link_seq_no,l]
                        for l in param.level_comosition
                          for node_seq_no in temp_safe_node_max
                            for link in network.node_list[node_seq_no].outgoing_link_list
                              if link.link_type in ['ur','dr']))>=1)
                    num+=1
            
                #到达节点不小于1
                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                temp_value=0
                for link in network.node_list[node_seq_no].incoming_link_list:
                    if link.link_type in ['ur','dr','cod','ucd']:
                        for l in param.level_comosition:
                            temp_value+=z_var[link.link_seq_no,l]
                if temp_value>1.1:        
                    model.cbLazy(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1)
                    num+=1
                    
                    
                    
                #出发节点不小于1
                temp_value=0
                for link in network.node_list[node_seq_no].outgoing_link_list:
                    if link.link_type in ['ur','dr']:
                        for l in param.level_comosition:
                            temp_value+=z_var[link.link_seq_no,l]
                if temp_value>1.1:
                    model.cbLazy(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                           if link.link_type in ['ur','dr']
                                                           for l in param.level_comosition) <= 1)
                
           
            
            # #列车能力约束
            # s=sec.from_node_id
            # run_dir=sec.run_direction
            # for t in range(param.max_time):                
                # # print(network.link_list[link_seq_no].link_type,link_seq_no)
                # # input()
                # node_index=(s,t,run_dir,1)
                # node_seq_no=network.node_index_to_no_dict[node_index]
                # temp_value=0
                # for w in sec.belong_OD_list:
                    # if param.earliest_time[w,s]<=t<=param.latest_time[w,s]:
                        # temp_value+=b_var[w,s,t]
                
                # temp_v1=0
                # for link in network.node_list[node_seq_no].outgoing_link_list:                    
                    # if link.link_type in ['ur','dr']:
                        # for l in param.level_comosition:
                            # temp_v1+=z_var[link.link_seq_no,l]*l*param.single_cap
                
                # if temp_value-temp_v1>=1:
                    # model.cbLazy(gb.quicksum(self.b_variable[w,s,t] for w in sec.belong_OD_list
                    # if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                    # <= gb.quicksum(self.z_variable[link.link_seq_no,l]*l*param.single_cap
                        # for link in network.node_list[node_seq_no].outgoing_link_list
                        # if link.link_type in ['ur','dr'] for l in param.level_comosition))                   
                    # num+=1
           
        for a in network.link_list:
            if a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                temp_value=0
                temp_v1=0
                for l in param.level_comosition:
                    for temp_link in network.node_list[from_seq_no].incoming_link_list:
                        if temp_link.link_type in ['ur','dr']:
                            temp_value+=z_var[temp_link.link_seq_no,l]*0.5+z_var[temp_link.link_seq_no,l]*l
                    
                    temp_v1+=z_var[link_seq_no,l]*l
                    
                if (temp_value-temp_v1)>=0.1:
                    model.cbLazy(gb.quicksum(self.z_variable[link_seq_no,l]*l for l in param.level_comosition) >=
                    gb.quicksum(gb.quicksum(self.z_variable[temp_link.link_seq_no,l]*l for l in param.level_comosition)+0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                            for temp_link in network.node_list[from_seq_no].incoming_link_list
                            if temp_link.link_type in ['ur','dr']))
                    num+=1
                    
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                temp_value=0
                temp_v1=0
                for l in param.level_comosition:
                    for temp_link in network.node_list[from_seq_no].incoming_link_list:
                        if temp_link.link_type in ['ur','dr']:
                            temp_value=z_var[temp_link.link_seq_no,l]*l-0.5*z_var[temp_link.link_seq_no,l]
                    temp_v1=z_var[link_seq_no,l]*l
                
                if (temp_v1-temp_value)>=0.1:
                    model.cbLazy(gb.quicksum(self.z_variable[link_seq_no,l]*l for l in param.level_comosition) <=
                    gb.quicksum(gb.quicksum(self.z_variable[temp_link.link_seq_no,l]*l for l in param.level_comosition)-0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                            for temp_link in network.node_list[from_seq_no].incoming_link_list
                            if temp_link.link_type in ['ur','dr']))
                    num+=1        
        
        
        ##passenger
        for w in demand.OD_list:
            if w not in param.key_OD_list:
                s=w[0];sp=w[1]
                run_dir=1 if s<sp else 2
                step=1 if s<sp else -1
                
                #passenger flow balance-inter
                for v in network.node_list:
                    if v.node_attr==1 and v.node_direction==run_dir and (s<v.node_id<sp or sp<v.node_id<s):
                        ts=v.node_id
                        tt=v.node_time                    
                        
                        if param.earliest_time[w,ts]<=tt<=param.latest_time[w,ts]:
                            temp_link_list=[]
                            temp_node={}
                            for link in v.incoming_link_list:
                                if link.link_type in ['dr','ur','ucd']:
                                    temp_link_list.append(link)
                                    if link.link_type in ['dr','ur']:
                                        temp_node[link.link_seq_no]=link.from_node_seq_no
                                    else:
                                        for t_link in network.node_list[link.from_node_seq_no].incoming_link_list:
                                            if t_link.link_type in ['dr','ur']:
                                                temp_node[link.link_seq_no]=t_link.from_node_seq_no
                                elif link.link_type in ['cod']:
                                    from_seq_no=link.from_node_seq_no
                                    for t_link in network.node_list[from_seq_no].incoming_link_list:
                                        if t_link.link_type in ['dr','ur']:
                                            temp_link_list.append(t_link)
                                            temp_node[t_link.link_seq_no]=t_link.from_node_seq_no
                                    
                            #new constraint
                            if len(temp_link_list)>0:                          
                                
                                # num0=0
                                # for temp_link in temp_link_list:
                                    # if param.earliest_time[w,network.node_list[temp_link.from_node_seq_no].node_id]<=network.node_list[temp_link.from_node_seq_no].node_time<=param.latest_time[w,network.node_list[temp_link.from_node_seq_no].node_id]:
                                        # num1=0
                                        # for l in param.level_comosition:
                                            # num1+=z_var[temp_link.link_seq_no,l]
                                        
                                        # num0+=num1*(b_var[w,network.node_list[temp_node[temp_link.link_seq_no]].node_id,network.node_list[temp_node[temp_link.link_seq_no]].node_time])
                                  
                                # if abs(num0-b_var[w,ts,tt])>0:                                
                                for temp_link in temp_link_list:
                                    pre_s=None
                                    pre_t=None
                                    if temp_link.link_type=='ucd':
                                        for t_link in network.node_list[temp_link.from_node_seq_no].incoming_link_list:
                                            if t_link.link_type in ['dr','ur']:
                                                from_node=t_link.from_node_seq_no
                                                pre_s=network.node_list[from_node].node_id
                                                pre_t=network.node_list[from_node].node_time
                                    else:
                                        from_node=temp_link.from_node_seq_no
                                        pre_s=network.node_list[from_node].node_id
                                        pre_t=network.node_list[from_node].node_time
                                    
                                    if pre_s!=None and pre_t!=None:
                                        if param.earliest_time[w,pre_s]<=pre_t<=param.latest_time[w,pre_s]:
                                            num0=0
                                            for l in param.level_comosition:
                                                num0+=z_var[temp_link.link_seq_no,l]
                                            
                                            if (num0-1)*(demand.demand_OD[w]+1)+b_var[w,pre_s,pre_t] > b_var[w,ts,tt]+1:
                                                model.cbLazy(self.b_variable[w,ts,tt]>=
                                                    (gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition)-1)*(demand.demand_OD[w]+1)+self.b_variable[w,pre_s,pre_t]
                                                    )
                                                    
                                                # model.cbLazy(self.b_variable[w,ts,tt]<=
                                                    # (1-gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition))*(demand.demand_OD[w]+1)+self.b_variable[w,pre_s,pre_t]
                                                    # )
                                                
                                                num+=1
                                        
            
                for sb in range(s,sp-step,step):
                    for t in range(param.earliest_time[w,sb],param.latest_time[w,sb]+1):
                        index=(sb,t,run_dir,1)
                        node_seq=network.node_index_to_no_dict[index]
                        temp_node_list=[]
                        temp_link_list=[]
                        for link in network.node_list[node_seq].outgoing_link_list:
                            if link.link_type in ['ur','dr']:
                                to_seq_no=link.to_node_seq_no
                                index=network.node_no_dict_to_index[to_seq_no]
                                tsp=index[0]
                                ttp=index[1]
                                if index[3]==1 and param.earliest_time[w,tsp]<=ttp<=param.latest_time[w,tsp]:
                                    if to_seq_no not in temp_node_list:
                                        temp_node_list.append(to_seq_no)
                                    
                                    temp_link_list.append(link.link_seq_no)
                                    
                                elif index[3]==2 and param.earliest_time[w,tsp]<=ttp+param.couple_time<=param.latest_time[w,tsp]:
                                    for t_link in network.node_list[to_seq_no].outgoing_link_list:
                                        if t_link.link_type in ['cod']:
                                            if t_link.to_node_seq_no not in temp_node_list:
                                                temp_node_list.append(t_link.to_node_seq_no)
                                    
                                    temp_link_list.append(link.link_seq_no)
                                    
                                elif index[3]==3 and param.earliest_time[w,tsp]<=ttp+param.uncouple_time<=param.latest_time[w,tsp]:
                                    for t_link in network.node_list[to_seq_no].outgoing_link_list:
                                        if t_link.link_type in ['ucd']:
                                            if t_link.to_node_seq_no not in temp_node_list:
                                                temp_node_list.append(t_link.to_node_seq_no)
                                            
                                            temp_link_list.append(t_link.link_seq_no)
                        # if w==(4,0) and sb==4 and t==2:
                            # print(temp_node_list)
                            # input()
                        # print(w,sb,t)
                        temp1=0
                        for t_node in temp_node_list:
                            for t_link in network.node_list[t_node].outgoing_link_list:
                                if t_link.link_type in ['ur','dr']:
                                    for l in param.level_comosition:
                                        temp1+=z_var[t_link.link_seq_no,l]
                        
                        # if b_var[w,sb,t]>temp1*demand.demand_OD[w]+1:
                            # model.cbLazy(self.b_variable[w,sb,t] <=
                                # (gb.quicksum(self.z_variable[t_link.link_seq_no,l]
                                 # for t_node in temp_node_list
                                 # for t_link in network.node_list[t_node].outgoing_link_list
                                 # if t_link.link_type in ['ur','dr']
                                 # for l in param.level_comosition)*(demand.demand_OD[w]))
                                # )
                        
                        temp2=0
                        for t_link_seq in temp_link_list:                      
                            for l in param.level_comosition:
                                temp2+=z_var[t_link_seq,l]
                            
                        if b_var[w,sb,t]>temp2*demand.demand_OD[w]+1:
                            model.cbLazy(self.b_variable[w,sb,t] <=
                                (gb.quicksum(self.z_variable[t_link_seq,l]
                                 for t_link_seq in temp_link_list                         
                                 for l in param.level_comosition)*(demand.demand_max[w]))
                                )
            
        
        num_O_cuts+=num
        print ("total add vailid ineq:",num) 
        # input()    
           
    def __intial_Benders_cut(self):
        for w in demand.OD_list:
            self.update_sub_model(w,object_INI.ini_b_v,object_INI.ini_z_v)
            self.dual_sub_model[w].optimize()
            
            # # print(object_BAC.dual_sub_model.status)
            # # input()
            
            # # self.dual_sub_model.computeIIS()
            # # self.dual_sub_model.write("xxx33.ilp")
            # # print("model,xxx333")
            # # input()       
            
            # self.__master_model.addConstr(self.obj_theta[w]>=
                            # (self.dual_pi_OD[w,self.OD_node[w[0]]].x*demand.demand_OD[w]
                                                    # -self.dual_pi_OD[w,self.OD_node[w[1]]].x*demand.demand_OD[w]
                                                    # +gb.quicksum(min(0,self.dual_lambda[w,s,t].x)*self.b_variable[w,s,t]                                                        
                                                        # for s in network.OD_station[w]
                                                        # if s!=w[1]
                                                        # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
                            # +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                                
                            
                            # +gb.quicksum(min(0,self.dual_gamma[link_seq_no].x)*param.single_cap*gb.quicksum(self.z_variable[link_seq_no[1],l]*l for l in param.level_comosition)
                                    # for link_seq_no in [key for key in self.dual_gamma.keys() if key[0] == w])
                            # ))
        
        # self.__master_model.update()
        
        object_INI.ini_b_v = {key: 0 for key, var in object_INI.b_v.items()}
        for w in demand.OD_list:
            self.update_sub_model(w,object_INI.ini_b_v,object_INI.ini_z_v)
            self.dual_sub_model[w].optimize()
            
            # print(object_BAC.dual_sub_model.status)
            # input()
            
            # self.dual_sub_model.computeIIS()
            # self.dual_sub_model.write("xxx33.ilp")
            # print("model,xxx333")
            # input()
            
            self.__master_model.addConstr(self.obj_theta[w]>=
                            (self.dual_pi_OD[w,self.OD_node[w[0]]].x*demand.demand_OD[w]
                                                    -self.dual_pi_OD[w,self.OD_node[w[1]]].x*demand.demand_OD[w]
                                                    +gb.quicksum(min(0,self.dual_lambda[w,s,t].x)*self.b_variable[w,s,t]                                                        
                                                        for s in network.OD_station[w]
                                                        if s!=w[1]
                                                        for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                                
                            
                            +gb.quicksum(min(0,self.dual_gamma[link_seq_no].x)*param.single_cap*gb.quicksum(self.z_variable[link_seq_no[1],l]*l for l in param.level_comosition)
                                    for link_seq_no in [key for key in self.dual_gamma.keys() if key[0] == w])
                            ))
        
        self.__master_model.update()
        
        
        # self.dual_sub_model_n.optimize()
        # self.__master_model.addConstr(gb.quicksum(self.obj_theta[w] for w in demand.OD_list)>=
                # (gb.quicksum(self.dual_pi_OD_n[w,self.OD_node_n[w[0]]].x*demand.demand_OD[w]
                                        # -self.dual_pi_OD_n[w,self.OD_node_n[w[1]]].x*demand.demand_OD[w]
                                        # +gb.quicksum(self.dual_lambda_n[w,t].x*self.b_variable[w,w[0],t]                                                        
                                            # for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                # +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            # for w in demand.OD_list)
                
                # +gb.quicksum(self.dual_gamma_n[link_seq_no].x*param.single_cap*gb.quicksum(self.z_variable[link_seq_no,l]*l for l in param.level_comosition)
                # for sec in network.section_list
                # for link_seq_no in (network.station_arc_run[sec.from_node_id,sec.run_direction] + network.uncouple_arc[sec.from_node_id,sec.run_direction] + network.couple_arc[sec.from_node_id,sec.run_direction]))
                # ))
        
        # self.__master_model.update()
        
    def process(self):
        # self.__reformulated_master_model()
        # input()
        
        # self.__master_model.Params.Cutoff = object_BAC.UB
        self.__master_model.params.outputflag = 1
        self.__master_pro()
        # self.__reformulated_master_model()        
        self.__master_model.update()        
        for w in demand.OD_list:
            self.dual_sub_pro(w)
        
        # print("*****")
        # self.dual_sub_pro_one()
        
        print("finish master model and dual subprob loading!")
        
        self.__intial_Benders_cut()
        
        # self.__master_model.optimize()
        # Output().output_result(self.__master_model,"G_M1_1")
        # print(param.weight_train*self.obj_train.x,self.obj_theta.x)   
        # print(self.waiting_time.x,self.vitual_time.x)
        # input()        
        # self.__reformulated_master_model()
        # Output().output_result(self.__pre_master_model,"G_M1_2")
        
        
        # self.__master_model.Params.TimeLimit=1000
        # self.__master_model.Params.BranchDir=-1
        self.__master_model.Params.lazyConstraints = 1        
        self.__master_model.optimize(mycallback)
        
        # self.__master_model.computeIIS()
        # self.__master_model.write("xxx33.ilp") 
        # print("模型MP不可行！！！")
        # input()
        
        Output().output_result_for_BAC(self.best_x_value)
        
        print("B.cuts.{}, O.cuts.{},initial.cuts.{}".format(num_B_cuts,num_O_cuts,len(demand.OD_list)))
        gap=100*(self.UB-self.LB)/self.UB    
        print("UB is {}, LB is {}, gap is {}.".format(self.UB,self.LB,gap))
        input() 
            
num_B_cuts=0
num_O_cuts=0
num_Gap_display=0
exp_node_list=[]
unit_period=140
vad_ine_list=[]
def mycallback_M0(model, where): #运行时请去掉M0 变为 mycallback
    global num_B_cuts,num_Gap_display,unit_period
    global exp_node_list,vad_ine_list
    # print(where)
    # input()
    if where == gb.GRB.Callback.MIPSOL or where == gb.GRB.Callback.MIPNODE:        
        flag_stop=False
        b_var=None
        z_var=None
        theta_var=None
        vit_time=None
        wait_time=None
        obj_train=None
        flag=0
        
        if where == gb.GRB.Callback.MIPSOL: #节点获得可行解
            print("STATUS1:",model.cbGet(gb.GRB.Callback.MIPSOL_OBJBST))
            b_var = model.cbGetSolution(object_BAC.b_variable)
            z_var = model.cbGetSolution(object_BAC.z_variable)
            theta_var = model.cbGetSolution(object_BAC.obj_theta)
            # vit_time = model.cbGetSolution(object_BAC.vitual_time)
            # wait_time= model.cbGetSolution(object_BAC.waiting_time)
            # obj_train= model.cbGetSolution(object_BAC.obj_train)
            
            # num_node=model.cbGet(gb.GRB.Callback.MIPSOL_NODCNT)
                       
            # print(model.cbGet(gb.GRB.Callback.MIPSOL_OBJ))
            # print(model.cbGet(gb.GRB.Callback.MIPSOL_OBJBST))
            # print(model.cbGet(gb.GRB.Callback.MIPSOL_OBJBND))
            # # print("vittime:",vit_time,wait_time,theta_var, param.weight_train*obj_train)
            # input() 

            # if model.cbGet(gb.GRB.Callback.MIPSOL_OBJ)<model.cbGet(gb.GRB.Callback.MIPSOL_OBJBST):
            # if num_node<1:
            flag_stop=True            
                        
            # object_BAC.add_valid_inequality(model,z_var,b_var)
            
            # unit_period=int(unit_period/2)
            # if unit_period>3:
                # add_valid_inequality_period(model,z_var,b_var,unit_period)
            # else:
                # unit_period=60
            
            if model.cbGet(gb.GRB.Callback.MIPSOL_OBJBST)<object_BAC.UB:
                object_BAC.UB=model.cbGet(gb.GRB.Callback.MIPSOL_OBJBST)
                # object_BAC.update_UB(z_var)
                print("UB:",object_BAC.UB)
                flag_stop=True 
            
            # object_BAC.LB=max(object_BAC.LB,model.cbGet(gb.GRB.Callback.MIPSOL_OBJBND))
            # # print(model.cbGet(gb.GRB.Callback.MIPSOL_OBJBND),object_BAC.LB,object_BAC.UB)
            # if 0<object_BAC.LB<object_BAC.UB<999999:
                # gap=100*(object_BAC.UB-object_BAC.LB)/object_BAC.UB
                # # print("gap1",gap)
                # if gap<0.001:
                    # model.terminate()            
            
        if where == gb.GRB.Callback.MIPNODE and model.cbGet(gb.GRB.Callback.MIPNODE_STATUS)==2: #节点获得松弛解，非整数可行解
            # print("STATUS2:",model.cbGet(gb.GRB.Callback.MIPNODE_STATUS))
            # input()
            b_var = model.cbGetNodeRel(object_BAC.b_variable)
            z_var = model.cbGetNodeRel(object_BAC.z_variable)
            theta_var = model.cbGetNodeRel(object_BAC.obj_theta)
            obj_train = model.cbGetNodeRel(object_BAC.obj_train)
            
            
            
            obj_pax=0
            for w in demand.OD_list:
               obj_pax+= theta_var[w]
            
            # print()
            # print("obj-pax:",obj_pax,"obj-train:",param.weight_train*obj_train)
            # input()
            
            
            # # obj_train = model.cbGetNodeRel(object_BAC.obj_train)
            # # unit_var = model.cbGetNodeRel(object_BAC.unit_num_start_var)
            
            # if model.cbGet(gb.GRB.Callback.RUNTIME)>200:
                # for sec in network.section_list:
                    # run_dir=sec.run_direction        
                    # from_node_id=sec.from_node_id
                    # to_node_id=sec.to_node_id
                    # num=0
                    # for link_seq in network.station_arc_run[sec.from_node_id,sec.run_direction]:
                        # for l in param.level_comosition:
                            # if z_var[link_seq,l]>0:
                                # print(run_dir)
                                # print(network.link_list[link_seq].start_time)
                                # print(network.link_list[link_seq].from_node_id)
                                # print(z_var[link_seq,l])
                            # input()
                            
                            # num+=z_var[link_seq,l]
                    # print(run_dir,from_node_id,num)
                    # input()           

            
            num_node=model.cbGet(gb.GRB.Callback.MIPNODE_NODCNT)  
            
            
            if num_node<1 or num_node%10==0:
                # # object_BAC.add_valid_inequality(model,z_var,b_var)
                flag_stop=True
                
                # add_valid_inequality_var(model,z_var,b_var)
                add_valid_inequality_OD(model,z_var,b_var)
                # add_valid_inequality_wait(model,z_var,b_var)
                
                # for t in range(param.train_early_time[1,0],param.train_latest_time[1,0]-2):
                    # num=0
                    # temp_link=[]
                    # for tp in range(t,param.train_latest_time[1,0]+1):
                        # index=(0,tp,1,1)
                        # node_seq=network.node_index_to_no_dict[index]
                        # for link in network.node_list[node_seq].outgoing_link_list:
                            # if link.link_type in ['ur']:
                                # temp_link.append(link.link_seq_no)
                                # for l in param.level_comosition:
                                    # num+=z_var[link.link_seq_no,l]*l
                        # if num>0.9:
                            # break
                    
                    # if num>0.9:
                        # model.cbLazy(gb.quicksum(object_BAC.z_variable[link_seq_no,l] for link_seq_no in temp_link
                                                    # for l in param.level_comosition)
                                    # >=1
                        # )
 
            if num_node%10==-1: #and num_node not in exp_node_list and model.cbGet(gb.GRB.Callback.RUNTIME)>0:
                print("***genering UB***",object_BAC.UB)
                flag_feasi,b_v,z_v=object_BAC.primary_pro_feasibleSol(z_var)
                
                exp_node_list.append(num_node)
                
                if flag_feasi==True:
                    # model.cbLazy(param.weight_train*object_BAC.obj_train+gb.quicksum(object_BAC.obj_theta[w] for w in demand.OD_list)
                                    # <=object_BAC.UB)
                    print("***UB***",object_BAC.UB)
                    flag_con_num=0
                    for w in demand.OD_list:
                        if w not in param.key_OD_list:
                            object_BAC.update_sub_model(w,b_v,z_v)
                            object_BAC.dual_sub_model[w].optimize()  
                            
                            if object_BAC.dual_sub_model[w].status == gb.GRB.OPTIMAL:
                              
                                OD_cut_val=object_BAC.dual_sub_model[w].objVal
                                
                                # if theta_var<OD_cut_val-0.05:   
                                if abs(theta_var[w]-OD_cut_val)>0.5:     
                                    model.cbLazy(object_BAC.obj_theta[w]>=
                                            (object_BAC.dual_pi_OD[w,object_BAC.OD_node[w[0]]].x*demand.demand_OD[w]
                                                                    -object_BAC.dual_pi_OD[w,object_BAC.OD_node[w[1]]].x*demand.demand_OD[w]
                                                                    +gb.quicksum(min(0,object_BAC.dual_lambda[w,s,t].x)*object_BAC.b_variable[w,s,t]                                                        
                                                                        for s in network.OD_station[w]
                                                                        if s!=w[1]
                                                                        for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
                                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                                            
                                            +gb.quicksum(min(0,object_BAC.dual_gamma[link_seq_no].x)*param.single_cap*gb.quicksum(object_BAC.z_variable[link_seq_no[1],l]*l for l in param.level_comosition)
                                                for link_seq_no in [key for key in object_BAC.dual_gamma.keys() if key[0] == w])
                                            ))
                                    
                                    flag_con_num+=1
                    print("Benders_cut_num_for_GUB:",flag_con_num)                    
            
            if model.cbGet(gb.GRB.Callback.RUNTIME)>5400:
                model.terminate()
          
            
        if flag_stop==True : #初始计算时间的添加目的是避免起始的不可行
            # print("STATUS3:")
            # input()
            # b_var = model.cbGetNodeRel(object_BAC.b_variable)
            flag_con_num=0
                        
            for w in demand.OD_list:
                # if w not in param.key_OD_list:
                if w not in []:
                    object_BAC.update_sub_model(w,b_var,z_var)
                    object_BAC.dual_sub_model[w].optimize()  
                    
                    if object_BAC.dual_sub_model[w].status == gb.GRB.OPTIMAL:
                      
                        OD_cut_val=object_BAC.dual_sub_model[w].objVal
                      
                        # print(w,theta_var[w],OD_cut_val,theta_var[w]-OD_cut_val)
                        # input()
                        if abs(theta_var[w]-OD_cut_val)>0.5:                
                            model.cbLazy(object_BAC.obj_theta[w]>=
                                    (object_BAC.dual_pi_OD[w,object_BAC.OD_node[w[0]]].x*demand.demand_OD[w]
                                                            -object_BAC.dual_pi_OD[w,object_BAC.OD_node[w[1]]].x*demand.demand_OD[w]
                                                            +gb.quicksum(min(0,object_BAC.dual_lambda[w,s,t].x)*object_BAC.b_variable[w,s,t]                                                        
                                                                for s in network.OD_station[w]
                                                                if s!=w[1]
                                                                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
                                    +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                                    
                                    +gb.quicksum(min(0,object_BAC.dual_gamma[link_seq_no].x)*param.single_cap*gb.quicksum(object_BAC.z_variable[link_seq_no[1],l]*l for l in param.level_comosition)
                                        for link_seq_no in [key for key in object_BAC.dual_gamma.keys() if key[0] == w])
                                    ))
                                    
                            flag_con_num+=1
                        
                    else:
                        print(object_BAC.dual_sub_model[w].status)
                        # output_test(b_var,z_var) 
                        # object_BAC.dual_sub_model.computeIIS()
                        # object_BAC.dual_sub_model.write("xxx33.ilp")
                        # for key in z_var.keys():
                            # if z_var[key]>0:
                                # print(key,z_var[key])
                                # input()
                                
                        print("dual subproblem is inf_unb.")
                        input()
                        # object_BAC.dual_sub_model[w].write("xxx33.lp")
               
            # num_B_cuts+=flag_con_num
            
            
            # object_BAC.dual_sub_model_n.optimize()
            # model.cbLazy(gb.quicksum(object_BAC.obj_theta[w] for w in demand.OD_list)>=
                # (gb.quicksum(object_BAC.dual_pi_OD_n[w,object_BAC.OD_node_n[w[0]]].x*demand.demand_OD[w]
                                        # -object_BAC.dual_pi_OD_n[w,object_BAC.OD_node_n[w[1]]].x*demand.demand_OD[w]
                                        # +gb.quicksum(object_BAC.dual_lambda_n[w,t].x*object_BAC.b_variable[w,w[0],t]                                                        
                                            # for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                # +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            # for w in demand.OD_list)
                
                # +gb.quicksum(object_BAC.dual_gamma_n[link_seq_no].x*param.single_cap*gb.quicksum(object_BAC.z_variable[link_seq_no,l]*l for l in param.level_comosition)
                # for sec in network.section_list
                # for link_seq_no in (network.station_arc_run[sec.from_node_id,sec.run_direction] + network.uncouple_arc[sec.from_node_id,sec.run_direction] + network.couple_arc[sec.from_node_id,sec.run_direction]))
                # ))
            
            # print("Benders_cut_num:",flag_con_num)
            # if flag_con_num>0:
                # input()
            
            
        # print("lb:",model.cbGet(gb.GRB.Callback.MIPNODE_OBJBND))
        
        # if where==gb.GRB.Callback.MIP:              
            # model.computeIIS()
            # model.write("xxx33.ilp") 
            # print("模型MP不可行！！！")
            # input()
        gap=100
        # if num_Gap_display%100==0:
        if object_BAC.LB!=0:
            gap=100*(object_BAC.UB-object_BAC.LB)/object_BAC.UB    
        # print("UB is {}, LB is {}, gap is {}.".format(object_BAC.UB,object_BAC.LB,gap))
        # input()
        # num_Gap_display+=1

def add_valid_inequality_period(model,z_var,b_var,unit_time):
    sec_list=[]
    for w in param.key_OD_list:
        run_dir=1 if w[0]<w[1] else 2
        if (run_dir,w[0]) not in sec_list:
            sec_list.append((run_dir,w[0]))
            
    for sec_index in sec_list:
        sec=network.sec_index_to_no_dict[sec_index[0],sec_index[1]]
        from_n=sec.from_node_id
        to_n=sec.to_node_id
        run_dir=sec.run_direction
        
        s=from_n
        
        rand_time=random.randint(param.train_early_time[run_dir,from_n], param.train_early_time[run_dir,from_n]+10)
        
        max_iter=int((param.train_latest_time[run_dir,from_n]-rand_time)/unit_time)
        
        # print(max_iter,param.train_latest_time[run_dir,from_n]-param.train_early_time[run_dir,from_n])
        # input()
        
        for pt in range(max_iter):
            if pt==max_iter-1:
                sta_time=pt*unit_time
                end_time=param.train_latest_time[run_dir,from_n]+1 
                vir_pax=param.vitual_pax_cost
            else:
                sta_time=pt*unit_time
                end_time=(pt+1)*unit_time
                vir_pax=1
            
            curr_arrive={}
            for w in sec.belong_OD_list:                
                if w[0]==from_n:
                    for t in range(sta_time,end_time):
                        # accum_arrive[t]=0
                        if t in curr_arrive.keys():
                            curr_arrive[t]+=demand.demand_dic[w,t]
                        else:
                            curr_arrive[t]=demand.demand_dic[w,t]
                        # for tp in range(param.train_early_time[run_dir,from_n],t+1):
                            # accum_arrive[t]+=demand.demand_dic[w,tp]
            
            
            
            val_obj=0
            for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]:
                if sta_time<=network.link_list[link_no].start_time<end_time:
                    for l in param.level_comosition:
                        val_obj+=param.weight_train*sec.sec_dis*z_var[link_no,l]*param.cost_composition[l] 
            
        
            for w in sec.belong_OD_list:
                if w[0]==s:
                    num1=0
                    for t in range(sta_time,end_time):
                        if param.earliest_time[w,s]<=t<=param.latest_time[w,s]:
                            num=0
                            for tp in range(sta_time,t+1):
                                if param.earliest_time[w,s]<=tp<=param.latest_time[w,s]:
                                    num+=b_var[w,w[0],tp]
                            
                            num1+=b_var[w,w[0],t]
                            
                            val_obj+=demand.demand_accum[w,t]-num
                
                    val_obj+=param.weight_pax*vir_pax*(demand.demand_OD[w]-num1)
                                        
              
              
            
        
            sec_model = gb.Model("sec_model")
            z=gb.tupledict()
            w_time=gb.tupledict()
            re_main=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='re_main')
            for t in range(sta_time,end_time):
                for l in param.level_comosition:
                    z[t,l]=sec_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(t,l))

                w_time[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='w_time[%d]'%(t))
              
            # sec_model.addConstr(gb.quicksum(z[t,l]*l for t in range(sta_time,end_time)
                                                   # for l in param.level_comosition)
                                                   # >= sec.max_train_unit,name="MC7")             
        
            sec_model.addConstr(gb.quicksum(z[t,l] for t in range(sta_time,end_time)
                                               for l in param.level_comosition)
                                               <= 30,name="MC71")
            
            
            for t in range(sta_time,end_time):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    tpp=tp+sec.run_time
                    if tpp<end_time+sec.run_time:
                        temp_safe_node.append(tp)
                
                temp_safe_node_max=[]
                if sta_time<=t<end_time-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        tpp=tp+sec.run_time
                        if tpp<end_time+sec.run_time:
                            temp_safe_node_max.append(tp)
                
                if len(temp_safe_node)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node))
                            <= 1,name="MC2[%d]"%(t))             
            

                if len(temp_safe_node_max)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node_max))
                            >= 1,name="MC21[%d]"%(t))
                
                if t>sta_time:     
                    sec_model.addConstr(w_time[t] >=
                            w_time[t-1]+curr_arrive[t]-param.single_cap*gb.quicksum(z[t,l]*l for l in param.level_comosition)
                    ,name="MC91[%d]"%(t))
                else:
                    sec_model.addConstr(w_time[t] >=
                            curr_arrive[t]-param.single_cap*gb.quicksum(z[t,l]*l for l in param.level_comosition)
                    ,name="MC91[%d]"%(t))

            if pt==max_iter-1:
                sec_model.addConstr(re_main >=
                        w_time[end_time-1]*param.vitual_pax_cost
                ,name="MC10")
            else:
                sec_model.addConstr(re_main >=
                        w_time[end_time-1]#*param.vitual_pax_cost
                ,name="MC10")
                          
            sec_model.setObjective(param.weight_pax*gb.quicksum(w_time[t]*param.wait_pax_cost
            for t in range(sta_time,end_time))
            +sec.sec_dis*param.weight_train*gb.quicksum(z[t,l]*param.cost_composition[l]
                for t in range(sta_time,end_time)
                    for l in param.level_comosition)
                    +param.weight_pax*re_main,gb.GRB.MINIMIZE)
        
            sec_model.update()
            sec_model.Params.outputflag=0
            # sec_model.Params.MIPGap=0.01
            # sec_model.Params.TimeLimit=15
            sec_model.optimize()
            
           
            val_obj = float(val_obj)           
            if val_obj<sec_model.objVal-1:
                model.cbLazy(param.weight_train*(
                        gb.quicksum(sec.sec_dis*object_BAC.z_variable[link_no,l]*param.cost_composition[l]                                                   
                                                for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                if sta_time<=network.link_list[link_no].start_time<end_time
                                                for l in param.level_comosition))
                        +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(object_BAC.b_variable[w,w[0],tp] for tp in range(sta_time,t+1) if param.earliest_time[w,s]<=tp<=param.latest_time[w,s]))
                                                                            for w in sec.belong_OD_list if w[0]==s
                                                                            for t in range(sta_time,end_time)
                                                                            if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                        
                        +param.weight_pax*vir_pax*gb.quicksum((demand.demand_OD[w]-gb.quicksum(object_BAC.b_variable[w,w[0],t] for t in range(sta_time,end_time)
                                                                if param.earliest_time[w,s]<=t<=param.latest_time[w,s]))
                                                                for w in sec.belong_OD_list if w[0]==s)
                        
                        >=sec_model.objVal
                )

def add_valid_inequality_OD_BAC(model,z_var,b_var):   #求解时请将BAC去掉，将函数名称写为“add_valid_inequality_OD” 
    for w in demand.OD_list:
    # for w in param.key_OD_list:
        if w not in vad_ine_list:
            s=w[0]
            sp=w[1]
            run_dir=1 if s<sp else 2
            step=1 if run_dir==1 else -1
            
            val_obj=0
            temp_link={}
            tt_sec_dis=0
            for sb in range(s,sp,step):
                sec=network.sec_index_to_no_dict[run_dir,sb]
                tt_sec_dis+=sec.sec_dis
                for link_no in network.station_arc_run[sb,run_dir]:
                    if param.earliest_time[w,sb]<=network.link_list[link_no].start_time<=param.latest_time[w,sb]:
                        temp_link[link_no]=sec.sec_dis
                        for l in param.level_comosition:
                            val_obj+=param.weight_train*sec.sec_dis*z_var[link_no,l]*param.cost_composition[l]  
          
            temp_OD=[]
            for wp in demand.OD_list:
                p_run_dir=1 if wp[0]<wp[1] else 2
                flag_ture=False
                if wp[0]==w[0] and wp[1]>=w[1] and p_run_dir==1 and p_run_dir==run_dir:
                    flag_ture=True
                    temp_OD.append(wp)
                elif wp[0]==w[0] and wp[1]<=w[1] and p_run_dir==2 and p_run_dir==run_dir:
                    flag_ture=True
                    temp_OD.append(wp)
                    
                if flag_ture==True:
                    num1=0                     
                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1):
                        num=0
                        for tp in range(param.earliest_time[wp,s],t+1):                            
                            num+=b_var[wp,wp[0],tp]
                        
                        val_obj+=param.weight_pax*param.wait_pax_cost*(demand.demand_accum[wp,t]-num)
                                           
                        num1 += b_var[wp,wp[0],t]
                        
                     
                    val_obj+=param.weight_pax*param.vitual_pax_cost*(max(0,demand.demand_OD[wp]-num1))
           
            # print(w,val_obj)
            # print(object_INI.lower_bound_OD[w])
            # input()
            
            if val_obj<object_INI.lower_bound_OD[w]-1:
                model.cbLazy(param.weight_train*(
                gb.quicksum(temp_link[link_no]*object_BAC.z_variable[link_no,l]*param.cost_composition[l]                                                   
                                        for link_no in temp_link.keys()                                    
                                        for l in param.level_comosition))
                +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[wp,t]-gb.quicksum(object_BAC.b_variable[wp,wp[0],tp] for tp in range(param.earliest_time[wp,wp[0]],t+1)))
                                                                    for wp in temp_OD
                                                                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1))
                +param.weight_pax*param.vitual_pax_cost*1*gb.quicksum((demand.demand_OD[wp]-gb.quicksum(object_BAC.b_variable[wp,wp[0],t]
                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1)))for wp in temp_OD)
                >=object_INI.lower_bound_OD[w]
                )
                
                model.cbLazy(param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[wp,t]-gb.quicksum(object_BAC.b_variable[wp,wp[0],tp] for tp in range(param.earliest_time[wp,wp[0]],t+1)))
                                                                    for wp in temp_OD
                                                                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1))
                +param.weight_pax*param.vitual_pax_cost*1*gb.quicksum((demand.demand_OD[wp]-gb.quicksum(object_BAC.b_variable[wp,wp[0],t]
                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1)))for wp in temp_OD)
                >=object_INI.lower_bound_OD_waittime[w]
                )
                
                vad_ine_list.append(w)

def add_valid_inequality_var(model,z_var,b_var):
    sec_list=[]
    for w in param.key_OD_list:
        run_dir=1 if w[0]<w[1] else 2
        if (run_dir,w[0]) not in sec_list:
            sec_list.append((run_dir,w[0]))
            
    for sec_index in sec_list:
        sec=network.sec_index_to_no_dict[sec_index[0],sec_index[1]]
        from_n=sec.from_node_id
        to_n=sec.to_node_id
        run_dir=sec.run_direction
        
        s=from_n
        
        for pt in range(param.train_early_time[run_dir,from_n],param.train_latest_time[run_dir,from_n]+1):
        
            val_obj=0
            for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]:
                if network.link_list[link_no].start_time>=pt:
                    for l in param.level_comosition:
                        val_obj+=param.weight_train*sec.sec_dis*z_var[link_no,l]*param.cost_composition[l]  
        
            for w in sec.belong_OD_list:
                if w[0]==s:
                    num1=0
                    arr_num=0
                    for t in range(pt-1,param.latest_time[w,s]+1):
                        if t>=max(pt,param.earliest_time[w,s]):
                            num=0
                            for tp in range(param.earliest_time[w,s],t+1):                            
                                num+=b_var[w,w[0],tp]
                            
                            val_obj+=param.weight_pax*param.wait_pax_cost*(demand.demand_accum[w,t]-num)
                        
                        
                        if param.earliest_time[w,s] <= t <=param.latest_time[w,s]:
                            num1 += b_var[w,w[0],t]
                            arr_num += demand.demand_dic[w,t]
                    
                    val_obj+=param.weight_pax*param.vitual_pax_cost*(max(0,arr_num-num1))
   
            curr_arrive={}
            other_arrive={}
            for w in sec.belong_OD_list:                
                if w[0]==from_n:
                    for t in range(pt,param.latest_time[w,w[0]]+1):
                        # accum_arrive[t]=0
                        if t in curr_arrive.keys():
                            curr_arrive[t]+=demand.demand_dic[w,t]
                        else:
                            curr_arrive[t]=demand.demand_dic[w,t]
                        # for tp in range(param.train_early_time[run_dir,from_n],t+1):
                            # accum_arrive[t]+=demand.demand_dic[w,tp]
                else:
                    w_run_dir=1 if w[0]<w[1] else 2
                    step =1 if w_run_dir==1 else -1
                    run_time=0
                    for sp in range(w[0],from_n,step):
                        sec_p=network.sec_index_to_no_dict[w_run_dir,sp]
                        run_time+=sec_p.run_time
                        
                    for t in range(max(pt,param.earliest_time[w,w[0]]),param.latest_time[w,w[0]]+1):
                        if pt<=t+run_time<=param.latest_time[w,from_n]:                        
                            if t+run_time in other_arrive.keys():
                                other_arrive[t+run_time]+=demand.demand_dic[w,t+run_time]
                            else:
                                other_arrive[t+run_time]=demand.demand_dic[w,t+run_time]
            

            for t in range(pt,param.train_latest_time[run_dir,from_n]+1):
                if t not in curr_arrive.keys():
                    curr_arrive[t]=0
                if t not in other_arrive.keys():
                    other_arrive[t]=0
            
            
            sec_model = gb.Model("sec_model")
            z=gb.tupledict()
            w_time=gb.tupledict()
            other_w_time=gb.tupledict()
            
            b_pax=gb.tupledict()
            other_b_pax=gb.tupledict()
            
            re_main=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='re_main')
            
            for t in range(pt,param.train_latest_time[run_dir,from_n]+1):
                for l in param.level_comosition:
                    z[t,l]=sec_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(t,l))

                w_time[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='w_time[%d]'%(t))
                other_w_time[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='o_w_time[%d]'%(t))
                
                b_pax[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='b_pax[%d]'%(t))
                other_b_pax[t]=sec_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='other_b_pax[%d]'%(t))
                
                
            # sec_model.addConstr(gb.quicksum(z[t,l]*l for t in range(pt,param.train_latest_time[run_dir,from_n]+1)
                                                   # for l in param.level_comosition)
                                                   # >= sec.max_train_unit,name="MC7")             
        
            sec_model.addConstr(gb.quicksum(z[t,l] for t in range(pt,param.train_latest_time[run_dir,from_n]+1)
                                                   for l in param.level_comosition)
                                                   <= 30,name="MC71")  
            
            for t in range(pt,param.train_latest_time[run_dir,from_n]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):
                    tpp=tp+sec.run_time
                    if tpp<param.train_latest_time[run_dir,from_n]+1:
                        temp_safe_node.append(tp)
                
                temp_safe_node_max=[]
                if pt<=t<param.train_latest_time[run_dir,from_n]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        tpp=tp+sec.run_time
                        if tpp<param.train_latest_time[run_dir,from_n]+1:
                            temp_safe_node_max.append(tp)
                
                if len(temp_safe_node)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node))
                            <= 1,name="MC2[%d]"%(t))             
            

                if len(temp_safe_node_max)>0:
                    sec_model.addConstr((gb.quicksum(z[tp,l] for l in param.level_comosition for tp in temp_safe_node_max))
                            >= 1,name="MC21[%d]"%(t))
                
                if t>pt:     
                    sec_model.addConstr(w_time[t] ==
                            w_time[t-1]+curr_arrive[t]-b_pax[t]
                    ,name="MC91[%d]"%(t))
                elif t==pt:
                    sec_model.addConstr(w_time[t] ==
                            curr_arrive[t]-b_pax[t]
                    ,name="MC91[%d]"%(t))
                    
                if t>pt:     
                    sec_model.addConstr(other_w_time[t] ==
                            other_w_time[t-1]+other_arrive[t]-other_b_pax[t]
                    ,name="MC92[%d]"%(t))
                elif t==pt:
                    sec_model.addConstr(other_w_time[t] ==
                            other_arrive[t]-other_b_pax[t]
                    ,name="MC92[%d]"%(t))
                    
                    
                sec_model.addConstr(other_b_pax[t]+b_pax[t]<=0.5*param.single_cap*gb.quicksum(l*z[t,l] for l in param.level_comosition)
                ,name="MC93[%d]"%(t))
                
                sec_model.addConstr((gb.quicksum(z[t,l] for l in param.level_comosition))
                            <= 1)

            sec_model.addConstr(re_main ==
                    (w_time[param.train_latest_time[run_dir,from_n]]+other_w_time[param.train_latest_time[run_dir,from_n]])*param.vitual_pax_cost
            ,name="MC10")
        
            sec_model.setObjective(gb.quicksum(w_time[t]
            for t in range(pt,param.train_latest_time[run_dir,from_n]+1))
            +param.weight_train*sec.sec_dis*gb.quicksum(z[t,l]*param.cost_composition[l]
                for t in range(pt,param.train_latest_time[run_dir,from_n]+1)
                    for l in param.level_comosition)
                    +re_main,gb.GRB.MINIMIZE)
        
            sec_model.update()
            sec_model.Params.outputflag=0
            sec_model.Params.MIPGap=0.01
            sec_model.Params.TimeLimit=600
            sec_model.optimize()
            
            # print(sec.section_id,pt,val_obj) 
            # print(sec_model.status,"***")
            # # input()
            # print(sec_model.objVal)
            # input()
                        
            
            if sec_model.status==2 and val_obj<sec_model.objVal-1:
                model.cbLazy(param.weight_train*(
                gb.quicksum(sec.sec_dis*object_BAC.z_variable[link_no,l]*param.cost_composition[l]                                                   
                                        for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                        if network.link_list[link_no].start_time>=pt
                                        for l in param.level_comosition))
                +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(object_BAC.b_variable[w,w[0],tp] for tp in range(param.earliest_time[w,w[0]],t+1)))
                                                                    for w in sec.belong_OD_list if w[0]==s
                                                                    for t in range(max(param.earliest_time[w,s],pt),param.latest_time[w,s]+1))
                +param.weight_pax*param.vitual_pax_cost*1*gb.quicksum((demand.demand_OD[w]-gb.quicksum(object_BAC.b_variable[w,w[0],t] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)))for w in sec.belong_OD_list if w[0]==s)
                >=sec_model.objVal
                )


def add_valid_inequality_wait(model,z_var,b_var):
    sec_list=[]
    # for w in param.key_OD_list:
    for w in demand.OD_list:
        run_dir=1 if w[0]<w[1] else 2
        if (run_dir,w[0]) not in sec_list:
            sec_list.append((run_dir,w[0]))
            
    for sec_index in sec_list:
        sec=network.sec_index_to_no_dict[sec_index[0],sec_index[1]]
        from_n=sec.from_node_id
        to_n=sec.to_node_id
        run_dir=sec.run_direction
        
        s=from_n
        
        # end_time=random.randint(param.train_early_time[run_dir,from_n]+1, param.train_latest_time[run_dir,from_n]-5)
        
        for t in range(param.train_early_time[run_dir,from_n]+3,param.train_latest_time[run_dir,from_n]-3):
            min_obj=0
            val_obj=0            
            for w in sec.belong_OD_list:
                if w[0]==s and param.earliest_time[w,w[0]]<=t-1<t+1<=param.latest_time[w,w[0]]:
                    min_obj+=min(demand.demand_dic[w,t], demand.demand_dic[w,t-1]+demand.demand_dic[w,t+1])
                    
                    
                    for tp in range(t-1,t+2):
                        num=0
                        for tpp in range(param.earliest_time[w,w[0]],tp+1):
                            num+=b_var[w,w[0],tpp]
                            
                        # w_pax=1 if tp<param.latest_time[w,w[0]] else param.vitual_pax_cost
                        val_obj+=param.weight_pax*(demand.demand_accum[w,tp]-num)
            
            # print(sec.section_id,min_obj,val_obj)
            # input()  
            
            if val_obj<min_obj-0.5:
                model.cbLazy(
                gb.quicksum((demand.demand_accum[w,tb]-gb.quicksum(object_BAC.b_variable[w,w[0],tp] for tp in range(param.earliest_time[w,w[0]],tb+1)))
                    for w in sec.belong_OD_list if w[0]==s
                    for tb in [t-1,t,t+1]
                    if param.earliest_time[w,w[0]]<=tb<=param.latest_time[w,w[0]]
                    )
                >=min_obj
                )


class Benders_BAC_onecuts_M0:#分解为主问题和若干个客流加载子问题
    def __init__(self):
        self.OD_node={}
        self.dual_pi_OD={}
        self.dual_lambda=gb.tupledict()
        self.dual_gamma=gb.tupledict()       
        self.b_variable=gb.tupledict()
        self.z_variable=gb.tupledict()
        
        self.OD_node_n={}
        self.dual_pi_OD_n={}
        self.dual_lambda_n=gb.tupledict()
        self.dual_gamma_n=gb.tupledict()  
        self.obj_dual_n=None
        self.dual_sub_model_n=gb.Model("dual_model")
  
  
        self.obj_dual={}
        self.obj_train=None
        self.obj_theta={}
        self.__master_model=gb.Model("master_model")
        self.__pre_master_model=gb.Model("pre_master_model")
        self.dual_sub_model={}        
        for w in demand.OD_list:
            self.dual_sub_model[w]=gb.Model("sub_model_"+str(w))
         
    
        self.LB=float('-inf')
        self.UB=float('inf')
                
        self.waiting_time={}
        self.vitual_time={}
                
        self.best_x_value={}
        
    def __master_pro(self):
        
        self.obj_train=self.__master_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_train')
        
        x=gb.tupledict()
        for a in network.link_list:
            #train-related varibles
            if a.link_type not in ['vp','vv']:
                x[a.link_seq_no]=self.__master_model.addVar(lb=0,ub=a.link_cap,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
                if a.link_type in ['ur','dr','cod','ucd']:        
                    if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                        x[a.link_seq_no].ub=0
                    
                    for l in param.level_comosition:
                        self.z_variable[a.link_seq_no,l]=self.__master_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        # self.z_variable[a.link_seq_no,l].lb = round(object_INI.z_v[a.link_seq_no,l])
                        # self.z_variable[a.link_seq_no,l].ub = round(object_INI.z_v[a.link_seq_no,l])
                        if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                            self.z_variable[a.link_seq_no,l].ub=0
        
        for run_dir in [1,2]:
            # for s in network.turnback_station_list:
            for s in range(param.num_station):
                # if s not in [0,param.num_station-1]:
                    for t in range(param.train_latest_time[run_dir,s]+1,param.max_time):
                        for v_type in [1,2,3]:
                            index=(s,t,run_dir,2)
                            if index in network.node_index_to_no_dict.keys():
                                node_seq=network.node_index_to_no_dict[index]
                                for link in network.node_list[node_seq].incoming_link_list:
                                    if link.link_type in ['dr','ur']:
                                        x[link.link_seq_no].ub=0
        
        for w in demand.OD_list:
            self.waiting_time[w]=self.__master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='waiting_time[%d,%d]'%(w[0],w[1]))
            self.vitual_time[w]=self.__master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='vitual_time[%d,%d]'%(w[0],w[1]))
        
            self.obj_theta[w]=self.__master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_theta[%d,%d]'%(w[0],w[1]))
            step=1 if w[0]<w[1] else -1
            for s in range(w[0],w[1],step):        
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                    self.b_variable[w,s,t]=self.__master_model.addVar(lb=0,ub=min(demand.demand_OD[w],2*param.single_cap),vtype=gb.GRB.CONTINUOUS,name='b[%d,%d,%d,%d]'%(w[0],w[1],s,t))

        #add constraints
        #train flow balance-starting outgoing
        node_seq_no=network.node_index_to_no_dict[(-1,-1,-1,-1)]
        self.__master_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list) == param.max_unit,name="MC1[-1]")
        
        #train flow balance-ending ingoing
        node_seq_no=network.node_index_to_no_dict[(-2,-2,-2,-2)]
        self.__master_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list) == param.max_unit,name="MC1[-2]")
        
        #train flow balance-inter node
        num=0
        for v in network.node_list:
            # print(v.node_id)
            if v.node_id>=0:
                self.__master_model.addConstr((gb.quicksum(x[a.link_seq_no] for a in v.outgoing_link_list if a.link_type not in ['vv','vp'])
                -gb.quicksum(x[a.link_seq_no] for a in v.incoming_link_list if a.link_type not in ['vv','vp']))
                == 0,name="MC1[%d]"%(num))                
                num+=1
        
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction      
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        # tpp=tp+sec.run_time
                        if tp<param.train_latest_time[run_dir,from_node_id]+1:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                
                if len(temp_safe_node)>0:
                    self.__master_model.addConstr((gb.quicksum(self.z_variable[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            <= 1,name="MC2[%d,%d,%d]"%(from_node_id,t,run_dir))
                                
                if len(temp_safe_node_max)>0:
                    self.__master_model.addConstr((gb.quicksum(self.z_variable[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node_max
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            >= 1,name="MC21[%d,%d,%d]"%(from_node_id,t,run_dir))          
                  

                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                
                self.__master_model.addConstr(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                       if link.link_type in ['ur','dr']
                                                       for l in param.level_comosition) <= 1,name="MC4[%d,%d,%d]"%(from_node_id,run_dir,t))
                
                
                self.__master_model.addConstr(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1,name="MC41[%d,%d,%d]"%(from_node_id,run_dir,t))
            
            for link_seq_no in (network.station_arc_run[from_node_id,run_dir] + network.uncouple_arc[from_node_id,run_dir] + network.couple_arc[from_node_id,run_dir]):
                self.__master_model.addConstr(gb.quicksum(l*self.z_variable[link_seq_no,l] for l in param.level_comosition) == x[link_seq_no],name="MC3[%d]"%(link_seq_no))             
            
            
            # self.__master_model.addConstr(gb.quicksum(self.z_variable[link_seq_no,l] for link_seq_no in network.station_arc_run[from_node_id,run_dir] for l in param.level_comosition) == 14)             
            
        
        for a in network.link_list:
            if a.link_type=='vt':
                link_seq_no=a.link_seq_no
                from_node_id=a.from_node_id
                to_node_id=a.to_node_id
                run_dir=a.link_direction
                if a.from_node_id<0:
                    self.__master_model.addConstr(x[link_seq_no] == network.init_unit[run_dir,to_node_id],name="MC5[%d]"%(link_seq_no))             
                else:
                    self.__master_model.addConstr(x[link_seq_no] >= network.end_unit[run_dir,from_node_id],name="MC5[%d]"%(link_seq_no))             
            
            elif a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no 
                self.__master_model.addConstr(x[link_seq_no] >=
                gb.quicksum(x[temp_link.link_seq_no]+0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no))
            
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                self.__master_model.addConstr(x[link_seq_no] <=
                gb.quicksum(x[temp_link.link_seq_no]-0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no)) 
        
        #passenger constraints    
        for w in demand.OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2        
            #cumulative constraints
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                self.__master_model.addConstr(gb.quicksum(self.b_variable[w,s,tp] for tp in range(t+1)
                            if param.earliest_time[w,s]<=tp<=param.latest_time[w,s])
                            <= demand.demand_accum[w,t],name="MC7[%d,%d,%d]"%(w[0],w[1],t))
                
                # index=(s,t,run_dir,1)
                # node_seq_no=network.node_index_to_no_dict[index]
        
        #passenger capacity
        for sec in network.section_list:
            s=sec.from_node_id
            run_dir=sec.run_direction
            to_node=sec.to_node_id
            
            for t in range(param.train_early_time[run_dir,s],param.train_latest_time[run_dir,s]+1): 
                node_index=(s,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                self.__master_model.addConstr(gb.quicksum(self.b_variable[w,s,t] for w in sec.belong_OD_list
                    if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                    <= gb.quicksum(x[link.link_seq_no]*param.single_cap
                        for link in network.node_list[node_seq_no].outgoing_link_list
                        if link.link_type in ['ur','dr']),name="MC8[%d,%d,%d,%d]"%(s,run_dir,t,1))
        
                # temp_link_list=[]
                # for link in network.node_list[node_seq_no].incoming_link_list:                    
                    # if link.link_type in ['ur','dr']:
                        # temp_link_list.append(link.link_seq_no)
                    # elif link.link_type in ['cod','ucd']:
                        # from_node_seq_no=link.from_node_seq_no
                        # for temp_link in network.node_list[from_node_seq_no].incoming_link_list:
                            # if temp_link.link_type in ['ur','dr']:
                                # temp_link_list.append(temp_link.link_seq_no)
                        
                # if len(temp_link_list)>0:
                    # self.__master_model.addConstr(gb.quicksum(self.b_variable[w,s,t] for w in sec.belong_OD_list
                        # if w[0]!=s
                        # if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                        # <= (gb.quicksum(self.z_variable[link_seq_no,l]*l*param.single_cap
                                            # for link_seq_no in temp_link_list
                                                # for l in param.level_comosition)
                                                # )
                            # ,name="MC8[%d,%d,%d,%d]"%(s,run_dir,t,2))
                
                
                
                # temp_link=[]
                # for tp in [t+1]:
                    # if param.train_early_time[run_dir,s]<=tp<=param.train_latest_time[run_dir,s]:
                        # index=(s,tp,run_dir,1)
                        # node_seq=network.node_index_to_no_dict[index]
                        # for link in network.node_list[node_seq].outgoing_link_list:
                            # if link.link_type in ['ur','dr']:
                                # temp_link.append(link.link_seq_no)
                
                
                # temp_link1=[]
                # for tp in [t-1]:
                    # if param.train_early_time[run_dir,s]<=tp<=param.train_latest_time[run_dir,s]:
                        # index=(s,tp,run_dir,1)
                        # node_seq=network.node_index_to_no_dict[index]
                        # for link in network.node_list[node_seq].outgoing_link_list:
                            # if link.link_type in ['ur','dr']:
                                # temp_link1.append(link.link_seq_no)
                
                # # print(len(temp_link))
                # # input()
                
                # self.__master_model.addConstr(gb.quicksum(self.b_variable[w,s,t] for w in sec.belong_OD_list if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                # <= (1-gb.quicksum(self.z_variable[link_seq_no,l] for link_seq_no in temp_link for l in param.level_comosition))*1800
                # )
                
                # # for w in demand.OD_list:
                # for w in param.key_OD_list:
                    # if w in sec.belong_OD_list and param.earliest_time[w,s]<=t<=param.latest_time[w,s]:
                        # self.__master_model.addConstr(self.b_variable[w,s,t]<=
                            # (1-gb.quicksum(self.z_variable[link_seq_no,l] for link_seq_no in temp_link for l in param.level_comosition))*demand.demand_max[w]
                            # )
                            
                    # if w in sec.belong_OD_list and param.earliest_time[w,s]<=t<=param.latest_time[w,s]:
                        # self.__master_model.addConstr(self.b_variable[w,s,t]<=
                            # (1-gb.quicksum(self.z_variable[link_seq_no,l] for link_seq_no in temp_link1 for l in param.level_comosition))*demand.demand_max[w]
                            # )


        # for w in demand.OD_list:
        for w in param.key_OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2
            step=1 if s<sp else -1
            
            #passenger flow balance-inter
            for v in network.node_list:
                if v.node_attr==1 and v.node_direction==run_dir and (s<v.node_id<sp or sp<v.node_id<s):
                    ts=v.node_id
                    tt=v.node_time
                    
                    
                    if param.earliest_time[w,ts]<=tt<=param.latest_time[w,ts]:
                        temp_link_list=[]
                        temp_node={}
                        for link in v.incoming_link_list:
                            if link.link_type in ['dr','ur','ucd']:
                                temp_link_list.append(link)
                                if link.link_type in ['dr','ur']:
                                    temp_node[link.link_seq_no]=link.from_node_seq_no
                                else:
                                    for t_link in network.node_list[link.from_node_seq_no].incoming_link_list:
                                        if t_link.link_type in ['dr','ur']:
                                            temp_node[link.link_seq_no]=t_link.from_node_seq_no
                            elif link.link_type in ['cod']:
                                from_seq_no=link.from_node_seq_no
                                for t_link in network.node_list[from_seq_no].incoming_link_list:
                                    if t_link.link_type in ['dr','ur']:
                                        temp_link_list.append(t_link)
                                        temp_node[t_link.link_seq_no]=t_link.from_node_seq_no
                        
                        #new constraint
                        if len(temp_link_list)>0:                          
                            for temp_link in temp_link_list:
                                pre_s=None
                                pre_t=None
                                if temp_link.link_type=='ucd':
                                    for t_link in network.node_list[temp_link.from_node_seq_no].incoming_link_list:
                                        if t_link.link_type in ['dr','ur']:
                                            from_node=t_link.from_node_seq_no
                                            pre_s=network.node_list[from_node].node_id
                                            pre_t=network.node_list[from_node].node_time
                                else:
                                    from_node=temp_link.from_node_seq_no
                                    pre_s=network.node_list[from_node].node_id
                                    pre_t=network.node_list[from_node].node_time
                                
                                if pre_s!=None and pre_t!=None:
                                    if param.earliest_time[w,pre_s]<=pre_t<=param.latest_time[w,pre_s]:
                                        self.__master_model.addConstr(self.b_variable[w,ts,tt]>=
                                            (gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition)-1)*(demand.demand_OD[w]+1)+self.b_variable[w,pre_s,pre_t]
                                            ,name="MC611[%d]"%(temp_link.link_seq_no))
                                            
                                        # # self.__master_model.addConstr(self.b_variable[w,ts,tt]<=
                                            # # (1-gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition))*(demand.demand_OD[w]+1)+self.b_variable[w,pre_s,pre_t]
                                            # # ,name="MC612[%d]"%(temp_link.link_seq_no))
                                            
                            # # self.__master_model.addConstr(self.b_variable[w,ts,tt] ==
                            # # (gb.quicksum(gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition)*self.b_variable[w,network.node_list[temp_node[temp_link.link_seq_no]].node_id,network.node_list[temp_node[temp_link.link_seq_no]].node_time]
                                    # # for temp_link in temp_link_list                                    
                                    # # if param.earliest_time[w,network.node_list[temp_link.from_node_seq_no].node_id]<=network.node_list[temp_link.from_node_seq_no].node_time<=param.latest_time[w,network.node_list[temp_link.from_node_seq_no].node_id]))                            
                            # # ,name="MC612[%d,%d,%d,%d]"%(w[0],w[1],ts,tt))
                            
                
            for sb in range(s,sp-step,step):
                for t in range(param.earliest_time[w,sb],param.latest_time[w,sb]+1):
                    index=(sb,t,run_dir,1)
                    node_seq=network.node_index_to_no_dict[index]
                    temp_node_list=[]
                    temp_link_list=[]
                    for link in network.node_list[node_seq].outgoing_link_list:
                        if link.link_type in ['ur','dr']:
                            to_seq_no=link.to_node_seq_no
                            index=network.node_no_dict_to_index[to_seq_no]
                            tsp=index[0]
                            ttp=index[1]
                            if index[3]==1 and param.earliest_time[w,tsp]<=ttp<=param.latest_time[w,tsp]:
                                if to_seq_no not in temp_node_list:
                                    temp_node_list.append(to_seq_no)
                                
                                temp_link_list.append(link.link_seq_no)
                                
                            elif index[3]==2 and param.earliest_time[w,tsp]<=ttp+param.couple_time<=param.latest_time[w,tsp]:
                                for t_link in network.node_list[to_seq_no].outgoing_link_list:
                                    if t_link.link_type in ['cod']:
                                        if t_link.to_node_seq_no not in temp_node_list:
                                            temp_node_list.append(t_link.to_node_seq_no)
                                
                                temp_link_list.append(link.link_seq_no)
                                
                            elif index[3]==3 and param.earliest_time[w,tsp]<=ttp+param.uncouple_time<=param.latest_time[w,tsp]:
                                for t_link in network.node_list[to_seq_no].outgoing_link_list:
                                    if t_link.link_type in ['ucd']:
                                        if t_link.to_node_seq_no not in temp_node_list:
                                            temp_node_list.append(t_link.to_node_seq_no)
                                        
                                        temp_link_list.append(t_link.link_seq_no)

                    # self.__master_model.addConstr(self.b_variable[w,sb,t] <=
                        # (gb.quicksum(self.z_variable[t_link.link_seq_no,l]
                         # for t_node in temp_node_list
                         # for t_link in network.node_list[t_node].outgoing_link_list
                         # if t_link.link_type in ['ur','dr']
                         # for l in param.level_comosition)*(demand.demand_OD[w]))
                        # ,name="MC613[%d,%d,%d,%d]"%(w[0],w[1],sb,t))
                        # 上面约束没用
                        
                    self.__master_model.addConstr(self.b_variable[w,sb,t] <=
                        (gb.quicksum(self.z_variable[t_link_seq,l]
                         for t_link_seq in temp_link_list                         
                         for l in param.level_comosition)*(2*demand.demand_max[w]))
                        ,name="MC614[%d,%d,%d,%d]"%(w[0],w[1],sb,t))
                            
        # #valid inequality
        # self.__master_model.addConstr(param.weight_train*self.obj_train+gb.quicksum(self.obj_theta[w] for w in demand.OD_list)
                            # >=object_INI.estimate_lower_bound,name="vInEq1")#object_INI.estimate_lower_bound 这个不等式没用
        
        
        # for sec in network.section_list:
            # run_dir=sec.run_direction
            # s=sec.from_node_id
            
            # self.__master_model.addConstr(param.weight_train*(
            # gb.quicksum(sec.sec_dis*self.z_variable[link_no,l]*param.cost_composition[l]                                                   
                                    # for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                    # for l in param.level_comosition))
            
            # # +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]
                # # for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir]))))
            
            # +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(self.b_variable[w,w[0],tp] for tp in range(param.earliest_time[w,w[0]],t+1)))
                                                                # for w in sec.belong_OD_list if w[0]==s
                                                                # for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
            # +param.weight_pax*param.vitual_pax_cost*1*gb.quicksum((demand.demand_OD[w]-gb.quicksum(self.b_variable[w,w[0],t] for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)))for w in sec.belong_OD_list if w[0]==s)
            # >=object_INI.sec_estimate_lower_bound[sec.section_id],name="MC9[%d,%d]"%(s,run_dir))
            
            # unit_time=30
            # sta_time=0
            # end_time=0
            # for pt in range(object_INI.max_period[sec.section_id]):
                # if pt==object_INI.max_period[sec.section_id]-1:
                    # sta_time=pt*unit_time
                    # end_time=param.train_latest_time[run_dir,s]+1
                    
                    # self.__master_model.addConstr(param.weight_train*(
                        # gb.quicksum(sec.sec_dis*self.z_variable[link_no,l]*param.cost_composition[l]                                                   
                                                # for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                # if sta_time<=network.link_list[link_no].start_time<end_time
                                                # for l in param.level_comosition))
                        # +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(self.b_variable[w,w[0],tp] for tp in range(sta_time,t+1) if param.earliest_time[w,s]<=tp<=param.latest_time[w,s]))
                                                                            # for w in sec.belong_OD_list if w[0]==s
                                                                            # for t in range(sta_time,end_time)
                                                                            # if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                        
                        # +param.weight_pax*param.vitual_pax_cost*gb.quicksum((demand.demand_OD[w]-gb.quicksum(self.b_variable[w,w[0],t] for t in range(sta_time,end_time)
                                                                # if param.earliest_time[w,s]<=t<=param.latest_time[w,s]))
                                                                # for w in sec.belong_OD_list if w[0]==s)
                        
                        # >=object_INI.lower_bound_period[sec.section_id,pt],name="MC9[%d,%d,%d]"%(s,run_dir,pt))
                

                
                
                # else:
                    # sta_time=pt*unit_time
                    # end_time=(pt+1)*unit_time
                    
                    # self.__master_model.addConstr(param.weight_train*(
                        # gb.quicksum(sec.sec_dis*self.z_variable[link_no,l]*param.cost_composition[l]                                                   
                                                # for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                # if sta_time<=network.link_list[link_no].start_time<end_time
                                                # for l in param.level_comosition))
                        # +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(self.b_variable[w,w[0],tp] for tp in range(sta_time,t+1) if param.earliest_time[w,s]<=tp<=param.latest_time[w,s]))
                                                                            # for w in sec.belong_OD_list if w[0]==s
                                                                            # for t in range(sta_time,end_time)
                                                                            # if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                        
                        # +param.weight_pax*1*gb.quicksum((demand.demand_OD[w]-gb.quicksum(self.b_variable[w,w[0],t] for t in range(sta_time,end_time)
                                                                # if param.earliest_time[w,s]<=t<=param.latest_time[w,s]))
                                                                # for w in sec.belong_OD_list if w[0]==s)
                        
                        # >=object_INI.lower_bound_period[sec.section_id,pt],name="MC9[%d,%d,%d]"%(s,run_dir,pt))
                
            
            # print(sec.section_id,object_INI.sec_estimate_lower_bound[sec.section_id])
            # input()
       
        # # #valid inequality
        # for w in demand.OD_list:
            # self.__master_model.addConstr(self.waiting_time[w] == gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(self.b_variable[w,w[0],tp] for tp in range(param.earliest_time[w,w[0]],t+1)))
                                            # for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1)
                                            # )*param.wait_pax_cost,name="waiting_time[%d,%d]"%(w[0],w[1]))
            # self.__master_model.addConstr(self.vitual_time[w] == param.vitual_pax_cost*((demand.demand_OD[w]-gb.quicksum(self.b_variable[w,w[0],t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1)))
                                                                    # )
                                         # ,name="vitual_timeMC9[%d,%d]"%(w[0],w[1]))
        
            # self.__master_model.addConstr(self.obj_theta[w] >= param.weight_pax*(self.waiting_time[w]+self.vitual_time[w]),name="MCB[%d,%d]"%(w[0],w[1]))             
            # #上面约束没用

        #objective function
        self.__master_model.addConstr(gb.quicksum(sec.sec_dis*self.z_variable[link_no,l]*param.cost_composition[l] 
                                                    for sec in network.section_list
                                                        for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                            for l in param.level_comosition)
                                    +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]                                    
                                    for s in range(param.num_station)
                                        for run_dir in [1,2]
                                            for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir])))
                                    == self.obj_train,name="MCA")

        
        self.__master_model.setObjective(param.weight_train*self.obj_train+gb.quicksum(self.obj_theta[w] for w in demand.OD_list),gb.GRB.MINIMIZE)
        
        
        for key in object_INI.last_link:
            if key in self.z_variable.keys():
                self.z_variable[key].ub=0
        
        
        # self.__master_model.params.outputflag = 0
        # self.__master_model.Params.MIPGap=0.001
        # self.__master_model.params.FeasibilityTol=0.0001
        
        # for key in self.z_variable.keys():
            # self.z_variable[key].start = object_INI.ini_z_v[key] 
            
        # for key in self.b_variable.keys():
            # self.b_variable[key].start = object_INI.ini_b_v[key]


    def __master_for_Benders_M0(self):
 
        self.obj_train=self.__master_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_train')
        
        x=gb.tupledict()
        for a in network.link_list:
            #train-related varibles
            if a.link_type not in ['vp','vv']:
                x[a.link_seq_no]=self.__master_model.addVar(lb=0,ub=a.link_cap,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
                if a.link_type in ['ur','dr','cod','ucd']:        
                    if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                        x[a.link_seq_no].ub=0
                    
                    for l in param.level_comosition:
                        self.z_variable[a.link_seq_no,l]=self.__master_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        # self.z_variable[a.link_seq_no,l].lb = round(object_INI.z_v[a.link_seq_no,l])
                        # self.z_variable[a.link_seq_no,l].ub = round(object_INI.z_v[a.link_seq_no,l])
                        if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                            self.z_variable[a.link_seq_no,l].ub=0


        # for t in range(param.max_time-param.couple_time,param.max_time):
        
        for run_dir in [1,2]:
            # for s in network.turnback_station_list:
            for s in range(param.num_station):
                # if s not in [0,param.num_station-1]:
                    for t in range(param.train_latest_time[run_dir,s]+1,param.max_time):
                        for v_type in [1,2,3]:
                            index=(s,t,run_dir,2)
                            if index in network.node_index_to_no_dict.keys():
                                node_seq=network.node_index_to_no_dict[index]
                                for link in network.node_list[node_seq].incoming_link_list:
                                    if link.link_type in ['dr','ur']:
                                        x[link.link_seq_no].ub=0
            
        # for w in demand.OD_list:
            # self.waiting_time[w]=self.__master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='waiting_time[%d,%d]'%(w[0],w[1]))
            # self.vitual_time[w]=self.__master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='vitual_time[%d,%d]'%(w[0],w[1]))
        
        self.obj_theta=self.__master_model.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_theta')
       
        #add constraints
        #train flow balance-starting outgoing
        node_seq_no=network.node_index_to_no_dict[(-1,-1,-1,-1)]
        self.__master_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list) == param.max_unit,name="MC1[-1]")
        
        #train flow balance-ending ingoing
        node_seq_no=network.node_index_to_no_dict[(-2,-2,-2,-2)]
        self.__master_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list) == param.max_unit,name="MC1[-2]")
        
        #train flow balance-inter node
        num=0
        for v in network.node_list:
            # print(v.node_id)
            if v.node_id>=0:
                self.__master_model.addConstr((gb.quicksum(x[a.link_seq_no] for a in v.outgoing_link_list if a.link_type not in ['vv','vp'])
                -gb.quicksum(x[a.link_seq_no] for a in v.incoming_link_list if a.link_type not in ['vv','vp']))
                == 0,name="MC1[%d]"%(num))                
                num+=1
        
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction      
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        # tpp=tp+sec.run_time
                        if tp<param.train_latest_time[run_dir,from_node_id]+1:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                
                if len(temp_safe_node)>0:
                    self.__master_model.addConstr((gb.quicksum(self.z_variable[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            <= 1,name="MC2[%d,%d,%d]"%(from_node_id,t,run_dir))
                                
                if len(temp_safe_node_max)>0:
                    self.__master_model.addConstr((gb.quicksum(self.z_variable[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node_max
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            >= 1,name="MC21[%d,%d,%d]"%(from_node_id,t,run_dir))          
                  

                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                
                self.__master_model.addConstr(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                       if link.link_type in ['ur','dr']
                                                       for l in param.level_comosition) <= 1,name="MC4[%d,%d,%d]"%(from_node_id,run_dir,t))
                
                
                self.__master_model.addConstr(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1,name="MC41[%d,%d,%d]"%(from_node_id,run_dir,t))
            
            for link_seq_no in (network.station_arc_run[from_node_id,run_dir] + network.uncouple_arc[from_node_id,run_dir] + network.couple_arc[from_node_id,run_dir]):
                self.__master_model.addConstr(gb.quicksum(l*self.z_variable[link_seq_no,l] for l in param.level_comosition) == x[link_seq_no],name="MC3[%d]"%(link_seq_no))             
            
            
            # self.__master_model.addConstr(gb.quicksum(self.z_variable[link_seq_no,l] for link_seq_no in network.station_arc_run[from_node_id,run_dir] for l in param.level_comosition) == 14)             
            
        
        for a in network.link_list:
            if a.link_type=='vt':
                link_seq_no=a.link_seq_no
                from_node_id=a.from_node_id
                to_node_id=a.to_node_id
                run_dir=a.link_direction
                if a.from_node_id<0:
                    self.__master_model.addConstr(x[link_seq_no] == network.init_unit[run_dir,to_node_id],name="MC5[%d]"%(link_seq_no))             
                else:
                    self.__master_model.addConstr(x[link_seq_no] >= network.end_unit[run_dir,from_node_id],name="MC5[%d]"%(link_seq_no))             
            
            elif a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no 
                self.__master_model.addConstr(x[link_seq_no] >=
                gb.quicksum(x[temp_link.link_seq_no]+0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no))
            
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                self.__master_model.addConstr(x[link_seq_no] <=
                gb.quicksum(x[temp_link.link_seq_no]-0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no)) 
    
      

        #objective function
        self.__master_model.addConstr(gb.quicksum(sec.sec_dis*self.z_variable[link_no,l]*param.cost_composition[l] 
                                                    for sec in network.section_list
                                                        for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                            for l in param.level_comosition)
                                    +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]                                    
                                    for s in range(param.num_station)
                                        for run_dir in [1,2]
                                            for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir])))
                                    == self.obj_train,name="MCA")

        
        self.__master_model.setObjective(param.weight_train*self.obj_train+self.obj_theta,gb.GRB.MINIMIZE)
        
        
        for key in object_INI.last_link:
            if key in self.z_variable.keys():
                self.z_variable[key].ub=0
        
        self.__master_model.update()
        
        # self.__master_model.params.outputflag = 0
        # self.__master_model.Params.MIPGap=0.00001
        # self.__master_model.params.FeasibilityTol=0.0001
        
        # for key in self.z_variable.keys():
            # self.z_variable[key].start = object_INI.ini_z_v[key] 
            
        # for key in self.b_variable.keys():
            # self.b_variable[key].start = object_INI.ini_b_v[key]
       

    def dual_sub_pro_one(self):
        self.obj_dual_n=self.dual_sub_model_n.addVar(lb=0,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_pax')

        #defined variables
        dual_pi=gb.tupledict()
        for w in demand.OD_list:
            s_ori=w[0]
            s_des=w[1]
            step=1 if s_ori<s_des else -1
            run_dir=1 if s_ori<s_des else 2
            
            for s in range(s_ori,s_des+step,step):
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):
                    for v_type in [1,2,3]:
                        index=(s,t,run_dir,v_type)
                        if index in network.node_index_to_no_dict.keys():                            
                            node_seq_no=network.node_index_to_no_dict[index] 
                            dual_pi[w,node_seq_no]=self.dual_sub_model_n.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='dual_pi[%d,%d,%d]'%(w[0],w[1],node_seq_no))
                            if v_type==1 and s==w[0]:
                                self.dual_lambda_n[w,t]=self.dual_sub_model_n.addVar(lb=-gb.GRB.INFINITY,ub=0,vtype=gb.GRB.CONTINUOUS,name='dual_lambda[%d,%d,%d]'%(w[0],w[1],node_seq_no))
                
                if s==s_ori or s==s_des:
                    index=(-100-s,-100-s,-100-s,-100-s)
                    node_seq_no=network.node_index_to_no_dict[index]
                    dual_pi[w,node_seq_no]=self.dual_sub_model_n.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='dual_pi[%d,%d,%d]'%(w[0],w[1],node_seq_no))
                    self.dual_pi_OD_n[w,node_seq_no]=dual_pi[w,node_seq_no]
                    self.OD_node_n[s]=node_seq_no
        
        #defined constraints
        for a in network.link_list:
            
            if a.link_type in ['ucd','cod','ur','dr']:
                self.dual_gamma_n[a.link_seq_no]=self.dual_sub_model_n.addVar(lb=-gb.GRB.INFINITY,ub=0,vtype=gb.GRB.CONTINUOUS,name='dual_gamma[%d]'%(a.link_seq_no))
            
            #pax-related varibles
            if a.link_type not in ['vt','tud','tdu','idl','ucr']:  
                from_node_seq_no=a.from_node_seq_no
                to_node_seq_no=a.to_node_seq_no
                
                for w in demand.OD_list:
                    flag1=0;flag2=0
                    run_dir=1 if w[0]<w[1] else 2
                    
                    if a.from_node_id>=0 and (w[1]<=a.from_node_id<=w[0] or w[0]<=a.from_node_id<=w[1]) and (param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]):
                        flag1=1
                    elif a.from_node_id<0:
                        flag1=1
                    if  a.to_node_id>=0 and (w[1]<=a.to_node_id<=w[0] or w[0]<=a.to_node_id<=w[1]) and (param.earliest_time[w,a.to_node_id]<=a.end_time<=param.latest_time[w,a.to_node_id]):
                        flag2=1
                    elif a.to_node_id<0:
                        flag2=1
                    
                    if a.link_type=='vv':
                        flag1=1
                        flag2=1

             
                    if (flag1==1) and (flag2==1):                   
                        if a.link_type=='vv' and a.from_node_id==w[0] and a.to_node_id==w[1]:                    
                            self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no] <= param.weight_pax*param.vitual_pax_cost,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                            
                        elif a.link_type=='vp' and (a.from_node_id==w[1] or a.to_node_id==w[0]) and a.link_direction==run_dir:
                            self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no] <= 0,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                            
                        elif a.link_type not in ['vv','vp'] and a.link_direction==run_dir:
                            if (w[0]<=a.from_node_id<=a.to_node_id<=w[1] or w[1]<=a.to_node_id<=a.from_node_id<=w[0]) and param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]:
                                if a.link_type in ['ur','dr']:
                                    index=network.node_no_dict_to_index[from_node_seq_no]
                                    temp_s=index[0]
                                    temp_t=index[1]
                                    temp_r=index[2]
                                    if a.from_node_id==w[0]:
                                        # print(w,temp_t,param.latest_time[w,temp_s]-temp_t)
                                        # input()
                                        self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no]+gb.quicksum(self.dual_lambda_n[w,t_ttp] for t_ttp in range(temp_t,param.latest_time[w,temp_s]+1))+self.dual_gamma_n[a.link_seq_no] <= -param.weight_pax*param.wait_pax_cost*1*(param.latest_time[w,temp_s]-temp_t+1),name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                                    else:
                                        self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no]+self.dual_gamma_n[a.link_seq_no] <= 0,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                                        # print(w,a.from_node_id,a.to_node_id,"test...")
                                        # input()
                                if a.link_type in ['ucd','cod']:
                                    self.dual_sub_model_n.addConstr(dual_pi[w,from_node_seq_no]-dual_pi[w,to_node_seq_no]+self.dual_gamma_n[a.link_seq_no] <= 0,name='MC1[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
        
        self.dual_sub_model_n.addConstr(0 == self.obj_dual_n, name='MC3')
        
        self.dual_sub_model_n.setObjective(self.obj_dual_n,gb.GRB.MAXIMIZE)
        self.dual_sub_model_n.update()
        self.dual_sub_model_n.params.outputflag = 0
        self.dual_sub_model_n.params.InfUnbdInfo = 1



    def update_sub_model_benders(self,w):
                
        # print(len(self.dual_sub_model.getConstrs())-1)
        self.dual_sub_model.remove(self.dual_sub_model.getConstrs()[len(self.dual_sub_model.getConstrs())-1])
        # print(self.dual_pi_OD[w,self.OD_node[w[0]]])
        # input()
        self.dual_sub_model.addConstr((self.dual_pi_OD[w,self.OD_node[w[0]]]*demand.demand_OD[w]
                                                    -self.dual_pi_OD[w,self.OD_node[w[1]]]*demand.demand_OD[w]
                                                    +gb.quicksum(self.dual_lambda[w,s,t]*max(0,self.b_variable[w,t].x)                                                        
                                                        for s in network.OD_station[w]
                                                        if s!=w[1]
                                                        for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1)) 
                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            )
                            +gb.quicksum(self.dual_gamma[w,link_seq_no]*param.single_cap*gb.quicksum(max(self.z_variable[link_seq_no,l].x,0)*l for l in param.level_comosition)
                                for link_seq_no in [key for key in self.dual_gamma.keys() if key[0] == w])
                            ==self.obj_dual[w], name='MC3')
        
        
        self.dual_sub_model[w].update()
        
    def update_sub_model(self,w,b_var,z_var):
        # print(len(self.dual_sub_model[w].getConstrs())-1)
        self.dual_sub_model[w].remove(self.dual_sub_model[w].getConstrs()[len(self.dual_sub_model[w].getConstrs())-1])
        # print(self.dual_pi_OD[w,self.OD_node[w[0]]])
        # input()
        self.dual_sub_model[w].addConstr((self.dual_pi_OD[w,self.OD_node[w[0]]]*demand.demand_OD[w]
                                                    -self.dual_pi_OD[w,self.OD_node[w[1]]]*demand.demand_OD[w]
                                                    +gb.quicksum(self.dual_lambda[w,s,t]*max(0,b_var[w,s,t])                                       
                                                        for s in network.OD_station[w]
                                                        if s!=w[1]
                                                        for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1))
                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            )
                            +gb.quicksum(self.dual_gamma[link_seq_no]*param.single_cap*gb.quicksum(max(z_var[link_seq_no[1],l],0)*l for l in param.level_comosition)
                               for link_seq_no in [key for key in self.dual_gamma.keys() if key[0] == w])
                            ==self.obj_dual[w], name='MC3')
        
        
        self.dual_sub_model[w].update()
        
        # self.dual_sub_model.write("xxx33.lp")
        # input()

       

    def update_sub_model_one(self,z_var):
        # print(len(self.dual_sub_model[w].getConstrs())-1)
        self.dual_sub_model_n.remove(self.dual_sub_model_n.getConstrs()[len(self.dual_sub_model_n.getConstrs())-1])
        # print(self.dual_pi_OD[w,self.OD_node[w[0]]])
        # input()
        self.dual_sub_model_n.addConstr(gb.quicksum((self.dual_pi_OD_n[w,self.OD_node_n[w[0]]]*demand.demand_OD[w]
                                                    -self.dual_pi_OD_n[w,self.OD_node_n[w[1]]]*demand.demand_OD[w]
                                                    +gb.quicksum(self.dual_lambda_n[w,t]*demand.demand_accum[w,t]                                                       
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            ) for w in demand.OD_list)                            
                            +gb.quicksum(self.dual_gamma_n[link_seq_no]*param.single_cap*gb.quicksum(max(z_var[link_seq_no,l],0)*l for l in param.level_comosition)
                                for sec in network.section_list
                                for link_seq_no in (network.station_arc_run[sec.from_node_id,sec.run_direction] + network.uncouple_arc[sec.from_node_id,sec.run_direction] + network.couple_arc[sec.from_node_id,sec.run_direction])
                                )
                            ==self.obj_dual_n)        
        
        self.dual_sub_model_n.update()


    def __update_feasible_link(self,flag,feasible_link,time_gap):        
        num_arc=0
        if flag==0:#==0表示将feasible_link中弧段的上界置为1
            for link_seq_no in feasible_link:                
                
                if num_arc>900:
                    break
                
                a=network.link_list[link_seq_no]
                if a.link_type in ['ur','dr']:  
                    s=a.from_node_id
                    sp=a.to_node_id
                    run_dir=a.link_direction
                    from_time=a.start_time
                    run_time=a.end_time-a.start_time
                    for t in range(max(from_time-time_gap,param.train_early_time[run_dir,s]),min(from_time+time_gap,param.train_latest_time[run_dir,s])+1):
                        from_index=(s,t,run_dir,1)
                        tp=t+run_time
                        if tp<=param.train_latest_time[run_dir,sp]:
                            for v_type in [1,2,3]:
                                to_index=(sp,tp,run_dir,v_type)
                                from_seq=None;to_seq=None
                                if from_index in network.node_index_to_no_dict.keys():
                                    from_seq=network.node_index_to_no_dict[from_index]
                                if to_index in network.node_index_to_no_dict.keys():
                                    to_seq=network.node_index_to_no_dict[to_index]
                                if from_seq!=None and to_seq!=None:
                                    link_index=(from_seq,to_seq)                                
                                    if link_index in network.link_index_to_no_dict.keys():
                                        temp_link_seq_no=network.link_index_to_no_dict[link_index]
                                        for l in param.level_comosition:
                                            # if object_INI.z_v[temp_link_seq_no,l].lb==1:
                                                # print(object_INI.z_v[temp_link_seq_no,l].ub,object_INI.z_v[temp_link_seq_no,l].lb)
                                                # input()
                                            object_INI.z_v[temp_link_seq_no,l].ub=1
                                        
                                        if temp_link_seq_no not in object_INI.feasible_link_for_bestSol:
                                            num_arc+=1
                                        
        elif flag==1:#表示feasible_link中的弧段上界恢复为0
            for link_seq_no in feasible_link:                
                
                if num_arc>900:
                    break
                
                a=network.link_list[link_seq_no]
                if a.link_type in ['ur','dr']:  
                    s=a.from_node_id
                    sp=a.to_node_id
                    run_dir=a.link_direction
                    from_time=a.start_time
                    run_time=a.end_time-a.start_time
                    for t in range(max(from_time-time_gap,param.train_early_time[run_dir,s]),min(from_time+time_gap,param.train_latest_time[run_dir,s])+1):
                        from_index=(s,t,run_dir,1)
                        tp=t+run_time
                        if tp<=param.train_latest_time[run_dir,sp]:
                            for v_type in [1,2,3]:
                                to_index=(sp,tp,run_dir,v_type)
                                from_seq=None;to_seq=None
                                if from_index in network.node_index_to_no_dict.keys():
                                    from_seq=network.node_index_to_no_dict[from_index]
                                if to_index in network.node_index_to_no_dict.keys():
                                    to_seq=network.node_index_to_no_dict[to_index]
                                if from_seq!=None and to_seq!=None:
                                    link_index=(from_seq,to_seq)  
                                    if link_index in network.link_index_to_no_dict.keys():
                                        temp_link_seq_no=network.link_index_to_no_dict[link_index]
                                        for l in param.level_comosition:
                                            object_INI.z_v[temp_link_seq_no,l].ub=0 

                                        if temp_link_seq_no not in object_INI.feasible_link_for_bestSol:
                                            num_arc+=1
                                            
        elif flag==3:#所有格置为0，1
            for key1 in [key for key in object_INI.z_v.keys() if key[1] == param.level_comosition[0]]: 
                link_seq_no=key1[0]              
                a=network.link_list[link_seq_no]
                if a.link_type in ['ur','dr']:  
                    s=a.from_node_id
                    sp=a.to_node_id
                    run_dir=a.link_direction
                    from_time=a.start_time
                    run_time=a.end_time-a.start_time
                    for t in range(max(from_time-time_gap,param.train_early_time[run_dir,s]),min(from_time+time_gap,param.train_latest_time[run_dir,s])+1):
                        from_index=(s,t,run_dir,1)
                        tp=t+run_time
                        if tp<=param.train_latest_time[run_dir,sp]:
                            for v_type in [1,2,3]:
                                to_index=(sp,tp,run_dir,v_type)
                                from_seq=None;to_seq=None
                                if from_index in network.node_index_to_no_dict.keys():
                                    from_seq=network.node_index_to_no_dict[from_index]
                                if to_index in network.node_index_to_no_dict.keys():
                                    to_seq=network.node_index_to_no_dict[to_index]
                                if from_seq!=None and to_seq!=None:
                                    link_index=(from_seq,to_seq)  
                                    if link_index in network.link_index_to_no_dict.keys():
                                        temp_link_seq_no=network.link_index_to_no_dict[link_index]
                                        for l in param.level_comosition:
                                            object_INI.z_v[temp_link_seq_no,l].ub=0
                                            object_INI.z_v[temp_link_seq_no,l].lb=0                                          
        
    def primary_pro_feasibleSol(self,z_var):
        flagture=False
        movestep=5 #移动步长
        localstep=0 #非移动
        b_v={}
        z_v={}
        
        #step 1 筛选了一部分弧段
        feasible_link=[]
        for key in z_var.keys():
            link_seq_no=key[0]
            if network.link_list[link_seq_no].link_type in ['dr','ur']:
                if abs(abs(z_var[key])-0.5)<=0.1:
                    feasible_link.append(link_seq_no)
        
        # print("len:",len(feasible_link))
        # object_INI.second_origin_model.update()
        
        self.__update_feasible_link(0,feasible_link,movestep) #利用筛选的弧段更新模型
        
        object_INI.second_origin_model.update()
        object_INI.second_origin_model.optimize()
        
        # print("generating UB:",self.UB,object_INI.second_origin_model.objVal)
        # input()
        
        # if object_INI.second_origin_model.SolCount>0:  #得到可行解        
        if self.UB>object_INI.second_origin_model.objVal+0.1 and object_INI.second_origin_model.SolCount>0:
                flagture=True
                self.UB=object_INI.second_origin_model.objVal            
                self.best_x_value={} 
                
                b_v = {key: var.X for key, var in object_INI.b_v.items()}
                z_v = {key: var.X for key, var in object_INI.z_v.items()}
                # print("UB1:",self.UB)
                
                # 清空可用弧
                self.__update_feasible_link(3,[],localstep)
                
                object_INI.feasible_link_for_bestSol=[]
                for key in object_INI.z_v.keys():
                    link_seq_no=key[0]
                    if abs(object_INI.z_v[key].x)>0.9:
                        object_INI.feasible_link_for_bestSol.append(link_seq_no)
                        self.best_x_value[key[0]]=round(key[1])
                
                #利用当前最优解更新可行弧
                self.__update_feasible_link(0,object_INI.feasible_link_for_bestSol,localstep)           
        else:
            self.__update_feasible_link(1,feasible_link,movestep)
            self.__update_feasible_link(0,object_INI.feasible_link_for_bestSol,localstep) 
        
        # self.LB=max(self.LB,temp_LB)  
        # gap=100*(self.UB-self.LB)/self.UB    
        # print("UB is {}, LB is {}, gap is {}.".format(self.UB,self.LB,gap))
        # input()
        # if flagture==True:
            # print("self.UB",self.UB)
            # input()
        
        object_INI.second_origin_model.update()
        return flagture,b_v,z_v
        
    
    def update_UB(self,z_var):  
        self.best_x_value={}               
        
        # 清空可用弧
        self.__update_feasible_link(3,[],0)
        
        object_INI.feasible_link_for_bestSol=[]
        for key in object_INI.z_v.keys():
            link_seq_no=key[0]
            if abs(object_INI.z_v[key].x)>0.9:
                object_INI.feasible_link_for_bestSol.append(link_seq_no)
                self.best_x_value[key[0]]=round(key[1])
        
        #利用当前最优解更新可行弧
        self.__update_feasible_link(0,object_INI.feasible_link_for_bestSol,0) 
    
    def add_valid_inequality(self,model,z_var,b_var):        
        # print("adding to inequality!")
        global num_O_cuts
        num=0
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction        
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                temp_value=0
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                        for link in network.node_list[node_seq_no].outgoing_link_list:
                            if link.link_type in ['ur','dr']:
                                for l in param.level_comosition:
                                    temp_value+=z_var[link.link_seq_no,l]
                
                temp_safe_node_max=[]
                temp_max_value=0
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        # tpp=tp+sec.run_time
                        if tp<=param.train_latest_time[run_dir,from_node_id]:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                            for link in network.node_list[node_seq_no].outgoing_link_list:
                                if link.link_type in ['ur','dr']:
                                    for l in param.level_comosition:
                                        temp_max_value+=z_var[link.link_seq_no,l]

                if temp_value>1.1 and len(temp_safe_node)>0:          
                    model.cbLazy((gb.quicksum(self.z_variable[link.link_seq_no,l]
                        for l in param.level_comosition
                          for node_seq_no in temp_safe_node
                            for link in network.node_list[node_seq_no].outgoing_link_list
                              if link.link_type in ['ur','dr']))<=1)
                    num+=1
                    
                if temp_max_value<0.9 and len(temp_safe_node_max)>0:
                    # print(temp_max_value,from_node_id,t,run_dir)
                    # print(temp_safe_node_max)
                    # input()
                    model.cbLazy((gb.quicksum(self.z_variable[link.link_seq_no,l]
                        for l in param.level_comosition
                          for node_seq_no in temp_safe_node_max
                            for link in network.node_list[node_seq_no].outgoing_link_list
                              if link.link_type in ['ur','dr']))>=1)
                    num+=1
            
                #到达节点不小于1
                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                temp_value=0
                for link in network.node_list[node_seq_no].incoming_link_list:
                    if link.link_type in ['ur','dr','cod','ucd']:
                        for l in param.level_comosition:
                            temp_value+=z_var[link.link_seq_no,l]
                if temp_value>1.1:        
                    model.cbLazy(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1)
                    num+=1
                    
                    
                    
                #出发节点不小于1
                temp_value=0
                for link in network.node_list[node_seq_no].outgoing_link_list:
                    if link.link_type in ['ur','dr']:
                        for l in param.level_comosition:
                            temp_value+=z_var[link.link_seq_no,l]
                if temp_value>1.1:
                    model.cbLazy(gb.quicksum(self.z_variable[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                           if link.link_type in ['ur','dr']
                                                           for l in param.level_comosition) <= 1)
                
           
            
            # #列车能力约束
            # s=sec.from_node_id
            # run_dir=sec.run_direction
            # for t in range(param.max_time):                
                # # print(network.link_list[link_seq_no].link_type,link_seq_no)
                # # input()
                # node_index=(s,t,run_dir,1)
                # node_seq_no=network.node_index_to_no_dict[node_index]
                # temp_value=0
                # for w in sec.belong_OD_list:
                    # if param.earliest_time[w,s]<=t<=param.latest_time[w,s]:
                        # temp_value+=b_var[w,s,t]
                
                # temp_v1=0
                # for link in network.node_list[node_seq_no].outgoing_link_list:                    
                    # if link.link_type in ['ur','dr']:
                        # for l in param.level_comosition:
                            # temp_v1+=z_var[link.link_seq_no,l]*l*param.single_cap
                
                # if temp_value-temp_v1>=1:
                    # model.cbLazy(gb.quicksum(self.b_variable[w,s,t] for w in sec.belong_OD_list
                    # if param.earliest_time[w,s]<=t<=param.latest_time[w,s])
                    # <= gb.quicksum(self.z_variable[link.link_seq_no,l]*l*param.single_cap
                        # for link in network.node_list[node_seq_no].outgoing_link_list
                        # if link.link_type in ['ur','dr'] for l in param.level_comosition))                   
                    # num+=1
           
        for a in network.link_list:
            if a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                temp_value=0
                temp_v1=0
                for l in param.level_comosition:
                    for temp_link in network.node_list[from_seq_no].incoming_link_list:
                        if temp_link.link_type in ['ur','dr']:
                            temp_value+=z_var[temp_link.link_seq_no,l]*0.5+z_var[temp_link.link_seq_no,l]*l
                    
                    temp_v1+=z_var[link_seq_no,l]*l
                    
                if (temp_value-temp_v1)>=0.1:
                    model.cbLazy(gb.quicksum(self.z_variable[link_seq_no,l]*l for l in param.level_comosition) >=
                    gb.quicksum(gb.quicksum(self.z_variable[temp_link.link_seq_no,l]*l for l in param.level_comosition)+0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                            for temp_link in network.node_list[from_seq_no].incoming_link_list
                            if temp_link.link_type in ['ur','dr']))
                    num+=1
                    
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                temp_value=0
                temp_v1=0
                for l in param.level_comosition:
                    for temp_link in network.node_list[from_seq_no].incoming_link_list:
                        if temp_link.link_type in ['ur','dr']:
                            temp_value=z_var[temp_link.link_seq_no,l]*l-0.5*z_var[temp_link.link_seq_no,l]
                    temp_v1=z_var[link_seq_no,l]*l
                
                if (temp_v1-temp_value)>=0.1:
                    model.cbLazy(gb.quicksum(self.z_variable[link_seq_no,l]*l for l in param.level_comosition) <=
                    gb.quicksum(gb.quicksum(self.z_variable[temp_link.link_seq_no,l]*l for l in param.level_comosition)-0.5*gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition) 
                            for temp_link in network.node_list[from_seq_no].incoming_link_list
                            if temp_link.link_type in ['ur','dr']))
                    num+=1        
        
        
        ##passenger
        for w in demand.OD_list:
            if w not in param.key_OD_list:
                s=w[0];sp=w[1]
                run_dir=1 if s<sp else 2
                step=1 if s<sp else -1
                
                #passenger flow balance-inter
                for v in network.node_list:
                    if v.node_attr==1 and v.node_direction==run_dir and (s<v.node_id<sp or sp<v.node_id<s):
                        ts=v.node_id
                        tt=v.node_time                    
                        
                        if param.earliest_time[w,ts]<=tt<=param.latest_time[w,ts]:
                            temp_link_list=[]
                            temp_node={}
                            for link in v.incoming_link_list:
                                if link.link_type in ['dr','ur','ucd']:
                                    temp_link_list.append(link)
                                    if link.link_type in ['dr','ur']:
                                        temp_node[link.link_seq_no]=link.from_node_seq_no
                                    else:
                                        for t_link in network.node_list[link.from_node_seq_no].incoming_link_list:
                                            if t_link.link_type in ['dr','ur']:
                                                temp_node[link.link_seq_no]=t_link.from_node_seq_no
                                elif link.link_type in ['cod']:
                                    from_seq_no=link.from_node_seq_no
                                    for t_link in network.node_list[from_seq_no].incoming_link_list:
                                        if t_link.link_type in ['dr','ur']:
                                            temp_link_list.append(t_link)
                                            temp_node[t_link.link_seq_no]=t_link.from_node_seq_no
                                    
                            #new constraint
                            if len(temp_link_list)>0:                          
                                
                                # num0=0
                                # for temp_link in temp_link_list:
                                    # if param.earliest_time[w,network.node_list[temp_link.from_node_seq_no].node_id]<=network.node_list[temp_link.from_node_seq_no].node_time<=param.latest_time[w,network.node_list[temp_link.from_node_seq_no].node_id]:
                                        # num1=0
                                        # for l in param.level_comosition:
                                            # num1+=z_var[temp_link.link_seq_no,l]
                                        
                                        # num0+=num1*(b_var[w,network.node_list[temp_node[temp_link.link_seq_no]].node_id,network.node_list[temp_node[temp_link.link_seq_no]].node_time])
                                  
                                # if abs(num0-b_var[w,ts,tt])>0:                                
                                for temp_link in temp_link_list:
                                    pre_s=None
                                    pre_t=None
                                    if temp_link.link_type=='ucd':
                                        for t_link in network.node_list[temp_link.from_node_seq_no].incoming_link_list:
                                            if t_link.link_type in ['dr','ur']:
                                                from_node=t_link.from_node_seq_no
                                                pre_s=network.node_list[from_node].node_id
                                                pre_t=network.node_list[from_node].node_time
                                    else:
                                        from_node=temp_link.from_node_seq_no
                                        pre_s=network.node_list[from_node].node_id
                                        pre_t=network.node_list[from_node].node_time
                                    
                                    if pre_s!=None and pre_t!=None:
                                        if param.earliest_time[w,pre_s]<=pre_t<=param.latest_time[w,pre_s]:
                                            num0=0
                                            for l in param.level_comosition:
                                                num0+=z_var[temp_link.link_seq_no,l]
                                            
                                            if (num0-1)*(demand.demand_OD[w]+1)+b_var[w,pre_s,pre_t] > b_var[w,ts,tt]+1:
                                                model.cbLazy(self.b_variable[w,ts,tt]>=
                                                    (gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition)-1)*(demand.demand_OD[w]+1)+self.b_variable[w,pre_s,pre_t]
                                                    )
                                                    
                                                # model.cbLazy(self.b_variable[w,ts,tt]<=
                                                    # (1-gb.quicksum(self.z_variable[temp_link.link_seq_no,l] for l in param.level_comosition))*(demand.demand_OD[w]+1)+self.b_variable[w,pre_s,pre_t]
                                                    # )
                                                
                                                num+=1
                                        
            
                for sb in range(s,sp-step,step):
                    for t in range(param.earliest_time[w,sb],param.latest_time[w,sb]+1):
                        index=(sb,t,run_dir,1)
                        node_seq=network.node_index_to_no_dict[index]
                        temp_node_list=[]
                        temp_link_list=[]
                        for link in network.node_list[node_seq].outgoing_link_list:
                            if link.link_type in ['ur','dr']:
                                to_seq_no=link.to_node_seq_no
                                index=network.node_no_dict_to_index[to_seq_no]
                                tsp=index[0]
                                ttp=index[1]
                                if index[3]==1 and param.earliest_time[w,tsp]<=ttp<=param.latest_time[w,tsp]:
                                    if to_seq_no not in temp_node_list:
                                        temp_node_list.append(to_seq_no)
                                    
                                    temp_link_list.append(link.link_seq_no)
                                    
                                elif index[3]==2 and param.earliest_time[w,tsp]<=ttp+param.couple_time<=param.latest_time[w,tsp]:
                                    for t_link in network.node_list[to_seq_no].outgoing_link_list:
                                        if t_link.link_type in ['cod']:
                                            if t_link.to_node_seq_no not in temp_node_list:
                                                temp_node_list.append(t_link.to_node_seq_no)
                                    
                                    temp_link_list.append(link.link_seq_no)
                                    
                                elif index[3]==3 and param.earliest_time[w,tsp]<=ttp+param.uncouple_time<=param.latest_time[w,tsp]:
                                    for t_link in network.node_list[to_seq_no].outgoing_link_list:
                                        if t_link.link_type in ['ucd']:
                                            if t_link.to_node_seq_no not in temp_node_list:
                                                temp_node_list.append(t_link.to_node_seq_no)
                                            
                                            temp_link_list.append(t_link.link_seq_no)
                        # if w==(4,0) and sb==4 and t==2:
                            # print(temp_node_list)
                            # input()
                        # print(w,sb,t)
                        temp1=0
                        for t_node in temp_node_list:
                            for t_link in network.node_list[t_node].outgoing_link_list:
                                if t_link.link_type in ['ur','dr']:
                                    for l in param.level_comosition:
                                        temp1+=z_var[t_link.link_seq_no,l]
                        
                        # if b_var[w,sb,t]>temp1*demand.demand_OD[w]+1:
                            # model.cbLazy(self.b_variable[w,sb,t] <=
                                # (gb.quicksum(self.z_variable[t_link.link_seq_no,l]
                                 # for t_node in temp_node_list
                                 # for t_link in network.node_list[t_node].outgoing_link_list
                                 # if t_link.link_type in ['ur','dr']
                                 # for l in param.level_comosition)*(demand.demand_OD[w]))
                                # )
                        
                        temp2=0
                        for t_link_seq in temp_link_list:                      
                            for l in param.level_comosition:
                                temp2+=z_var[t_link_seq,l]
                            
                        if b_var[w,sb,t]>temp2*demand.demand_OD[w]+1:
                            model.cbLazy(self.b_variable[w,sb,t] <=
                                (gb.quicksum(self.z_variable[t_link_seq,l]
                                 for t_link_seq in temp_link_list                         
                                 for l in param.level_comosition)*(demand.demand_max[w]))
                                )
            
        
        num_O_cuts+=num
        print ("total add vailid ineq:",num) 
        # input()    
            
    def __intial_Benders_cut(self): 
        # print(len(self.dual_sub_model[w].getConstrs())-1)
        self.update_sub_model_one(object_INI.ini_z_v)
        self.dual_sub_model_n.optimize()
        
        self.__master_model.addConstr(self.obj_theta>=
                (gb.quicksum((self.dual_pi_OD_n[w,self.OD_node_n[w[0]]].x*demand.demand_OD[w]
                                                    -self.dual_pi_OD_n[w,self.OD_node_n[w[1]]].x*demand.demand_OD[w]
                                                    +gb.quicksum(self.dual_lambda_n[w,t].x*demand.demand_accum[w,t]                                                        
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            ) for w in demand.OD_list)                            
                            +gb.quicksum(self.dual_gamma_n[link_seq_no].x*param.single_cap*gb.quicksum(self.z_variable[link_seq_no,l]*l for l in param.level_comosition)
                                for sec in network.section_list
                                for link_seq_no in (network.station_arc_run[sec.from_node_id,sec.run_direction] + network.uncouple_arc[sec.from_node_id,sec.run_direction] + network.couple_arc[sec.from_node_id,sec.run_direction])
                                ))
               ,name="ini_cut")
        
        self.__master_model.update()
        
    
    def process(self):
        # self.__reformulated_master_model()
        # input()      
        
        self.__master_model.params.outputflag = 1
        self.__master_for_Benders_M0()       
        self.dual_sub_pro_one()
        
        # print("*****")
        # self.dual_sub_pro_one()
        
        print("finish master model and dual subprob loading!")
        
        self.__intial_Benders_cut()
        
        # self.__master_model.optimize()
        # Output().output_result(self.__master_model,"G_M1_1")
        # print(param.weight_train*self.obj_train.x,self.obj_theta.x)   
        # print(self.waiting_time.x,self.vitual_time.x)
        # input()        
        # self.__reformulated_master_model()
        # Output().output_result(self.__pre_master_model,"G_M1_2")        
        
        # self.__master_model.Params.TimeLimit=1000
        # self.__master_model.Params.BranchDir=-1
        self.__master_model.Params.lazyConstraints = 1 
        # self.__master_model.setParam('Heuristics', 0)        
        self.__master_model.optimize(mycallback)
        
        # self.__master_model.computeIIS()
        # self.__master_model.write("xxx33.ilp") 
        # print("模型MP不可行！！！")
        # input()
        
        Output().output_result_for_BAC(self.best_x_value)
        
        print("B.cuts.{}, O.cuts.{},initial.cuts.{}".format(num_B_cuts,num_O_cuts,len(demand.OD_list)))
        gap=100*(self.UB-self.LB)/self.UB    
        print("UB is {}, LB is {}, gap is {}.".format(self.UB,self.LB,gap))
        input() 
            
num_B_cuts=0
num_O_cuts=0
num_Gap_display=0
exp_node_list=[]
unit_period=140
vad_ine_list=[]
def mycallback_M1(model, where):
    global num_B_cuts,num_Gap_display,unit_period
    global exp_node_list,vad_ine_list
    # print(where)
    # input()    
    if where == gb.GRB.Callback.MIPSOL or where == gb.GRB.Callback.MIPNODE:        
        flag_stop=False
        b_var=None
        z_var=None
        theta_var=None
        vit_time=None
        wait_time=None
        obj_train=None
        flag=0
        test_stop=0
        # print(where)
        if where == gb.GRB.Callback.MIPSOL: #节点获得可行解
            # print("STATUS1:",model.cbGet(gb.GRB.Callback.MIPSOL_OBJ))
            # b_var = model.cbGetSolution(object_BAC_M0.b_variable)
            z_var = model.cbGetSolution(object_BAC_M0.z_variable)
            theta_var = model.cbGetSolution(object_BAC_M0.obj_theta)
            # vit_time = model.cbGetSolution(object_BAC_M0.vitual_time)
            # wait_time= model.cbGetSolution(object_BAC_M0.waiting_time)
            # obj_train= model.cbGetSolution(object_BAC_M0.obj_train)
            
            # num_node=model.cbGet(gb.GRB.Callback.MIPSOL_NODCNT)
                       
            # print(model.cbGet(gb.GRB.Callback.MIPSOL_OBJ))
            # print(model.cbGet(gb.GRB.Callback.MIPSOL_OBJBST))
            # print(model.cbGet(gb.GRB.Callback.MIPSOL_OBJBND))
            # # print("vittime:",vit_time,wait_time,theta_var, param.weight_train*obj_train)
            # input()         

            # if model.cbGet(gb.GRB.Callback.MIPSOL_OBJ)<model.cbGet(gb.GRB.Callback.MIPSOL_OBJBST):
            # if num_node<1:
            flag_stop=True
                        
            # object_BAC_M0.add_valid_inequality(model,z_var,b_var)
            
            # unit_period=int(unit_period/2)
            # if unit_period>3:
                # add_valid_inequality_period(model,z_var,b_var,unit_period)
            # else:
                # unit_period=60
            
            if model.cbGet(gb.GRB.Callback.MIPSOL_OBJBST)<object_BAC_M0.UB:
                object_BAC_M0.UB=model.cbGet(gb.GRB.Callback.MIPSOL_OBJBST)
                # object_BAC_M0.update_UB(z_var)
                print("UB:",object_BAC_M0.UB)
                flag_stop=True 
            
            # object_BAC_M0.LB=max(object_BAC_M0.LB,model.cbGet(gb.GRB.Callback.MIPSOL_OBJBND))
            # # print(model.cbGet(gb.GRB.Callback.MIPSOL_OBJBND),object_BAC_M0.LB,object_BAC_M0.UB)
            # if 0<object_BAC_M0.LB<object_BAC_M0.UB<999999:
                # gap=100*(object_BAC_M0.UB-object_BAC_M0.LB)/object_BAC_M0.UB
                # # print("gap1",gap)
                # if gap<0.001:
                    # model.terminate()
            # if model.cbGet(gb.GRB.Callback.MIPSOL_OBJ)<6873:
                # print(flag_stop)
                # test_stop=1
                # # input()
            
        if where == gb.GRB.Callback.MIPNODE and model.cbGet(gb.GRB.Callback.MIPNODE_STATUS)==2: #节点获得松弛解，非整数可行解
            
            # status = model.cbGet(gb.GRB.Callback.MIPNODE_STATUS)
            # if status == gb.GRB.OPTIMAL:
                # print("STATUS2:",model.cbGet(gb.GRB.Callback.MIPNODE_OBJBND))
            # input()
            
            # b_var = model.cbGetNodeRel(object_BAC_M0.b_variable)
            z_var = model.cbGetNodeRel(object_BAC_M0.z_variable)
            theta_var = model.cbGetNodeRel(object_BAC_M0.obj_theta)
            obj_train = model.cbGetNodeRel(object_BAC_M0.obj_train)
            
            
            num_node=model.cbGet(gb.GRB.Callback.MIPNODE_NODCNT)
            
            
            # if num_node<1 or num_node%10==0:
                # # object_BAC_M0.add_valid_inequality(model,z_var,b_var)
                # flag_stop=True
                
            
            if model.cbGet(gb.GRB.Callback.RUNTIME)>5400:
                model.terminate()
          
            
        if flag_stop==True : #初始计算时间的添加目的是避免起始的不可行
            # print("STATUS3:")
            # input()
            # b_var = model.cbGetNodeRel(object_BAC_M0.b_variable)
            flag_con_num=0
            
            object_BAC_M0.update_sub_model_one(z_var)
            object_BAC_M0.dual_sub_model_n.optimize()
            
            # print(object_BAC_M0.dual_sub_model_n.objVal)
            # input()
            
            model.cbLazy(object_BAC_M0.obj_theta>=
                (gb.quicksum((object_BAC_M0.dual_pi_OD_n[w,object_BAC_M0.OD_node_n[w[0]]].x*demand.demand_OD[w]
                                                    -object_BAC_M0.dual_pi_OD_n[w,object_BAC_M0.OD_node_n[w[1]]].x*demand.demand_OD[w]
                                                    +gb.quicksum(object_BAC_M0.dual_lambda_n[w,t].x*demand.demand_accum[w,t]                                                        
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            +param.weight_pax*param.wait_pax_cost*gb.quicksum(demand.demand_accum[w,t] for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))
                            ) for w in demand.OD_list)
                            +gb.quicksum(object_BAC_M0.dual_gamma_n[link_seq_no].x*param.single_cap*gb.quicksum(object_BAC_M0.z_variable[link_seq_no,l]*l for l in param.level_comosition)
                                for sec in network.section_list
                                for link_seq_no in (network.station_arc_run[sec.from_node_id,sec.run_direction] + network.uncouple_arc[sec.from_node_id,sec.run_direction] + network.couple_arc[sec.from_node_id,sec.run_direction])
                                ))
                )
                
            # if test_stop==1:
                # print("Benders_cut_num:",flag_con_num)
                # input()
            # flag_con_num+=1
            # print("Benders_cut_num:",flag_con_num)
            # if flag_con_num>0:
                # input()
            
            
        # print("lb:",model.cbGet(gb.GRB.Callback.MIPNODE_OBJBND))
        
        # if where==gb.GRB.Callback.MIP:              
            # model.computeIIS()
            # model.write("xxx33.ilp") 
            # print("模型MP不可行！！！")
            # input()
        gap=100
        # if num_Gap_display%100==0:
        if object_BAC_M0.LB!=0:
            gap=100*(object_BAC_M0.UB-object_BAC_M0.LB)/object_BAC_M0.UB    
        # print("UB is {}, LB is {}, gap is {}.".format(object_BAC.UB,object_BAC.LB,gap))
        # input()
        # num_Gap_display+=1

class Gurobi_Callback_M0:
    def __init__(self):
        self.__origin_model = gb.Model("origin_model")
        self.b_variable=gb.tupledict()
        self.z=gb.tupledict()
        
        
    def origin_model(self):
        obj_train=self.__origin_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_train')
        obj_pax=self.__origin_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_pax')
        x=gb.tupledict()
        y=gb.tupledict()
        # z=gb.tupledict()
        for a in network.link_list:
            #train-related varibles
            if a.link_type not in ['vp','vv']:
                x[a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=a.link_cap,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
                if a.link_type in ['ur','dr','cod','ucd']:        
                    
                    if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                        x[a.link_seq_no].ub=0
                    
                    for l in param.level_comosition:
                        self.z[a.link_seq_no,l]=self.__origin_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        
                        if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                            self.z[a.link_seq_no,l].ub=0
         
            #pax-related varibles
            if a.link_type not in ['vt','tud','tdu','idl','ucr']:
                for w in demand.OD_list:
                    run_dir=1 if w[0]<w[1] else 2 
                    
                    if a.link_type=='vv' and a.from_node_id==w[0] and a.to_node_id==w[1]:
                        y[w,a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                    elif a.link_type=='vp' and (a.from_node_id==w[1] or a.to_node_id==w[0]) and a.link_direction==run_dir:
                        y[w,a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                    
                    elif a.link_type not in ['vv','vp'] and a.link_direction==run_dir:                        
                        if (w[0]<=a.from_node_id<=a.to_node_id<=w[1] or w[1]<=a.to_node_id<=a.from_node_id<=w[0]) and param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]:
                            if a.link_type in ['ur','dr']:                            
                                y[w,a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        
                            if a.link_type in ['ucd','cod']:
                                y[w,a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        
                        
                        # if w[1]<=a.to_node_id<a.from_node_id<=w[0]:
                            # print(w,a.to_node_id,a.from_node_id,w[0],w[1])
                            # input()
                            
        for t in range(param.max_time-param.couple_time,param.max_time):
            for s in network.turnback_station_list:
                if s not in [0,param.num_station-1]:
                    for run_dir in [1,2]:
                        index=(s,t,run_dir,2)
                        node_seq=network.node_index_to_no_dict[index]
                        for link in network.node_list[node_seq].incoming_link_list:
                            if link.link_type in ['dr','ur']:
                                x[link.link_seq_no].ub=0                    
                            
        
        for w in demand.OD_list:            
            step=1 if w[0]<w[1] else -1
            for s in range(w[0],w[1],step):             
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                
                    self.b_variable[w,s,t]=self.__origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='b[%d,%d,%d,%d]'%(w[0],w[1],s,t))

       
        #add constraints
        #train flow balance-starting outgoing
        node_seq_no=network.node_index_to_no_dict[(-1,-1,-1,-1)]
        self.__origin_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list) == param.max_unit,name="MC1[-1]")
        
        #train flow balance-ending ingoing
        node_seq_no=network.node_index_to_no_dict[(-2,-2,-2,-2)]
        self.__origin_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list) == param.max_unit,name="MC1[-2]")
        
        #train flow balance-inter node
        num=0
        for v in network.node_list:
            # print(v.node_id)
            if v.node_id>=0:
                self.__origin_model.addConstr((gb.quicksum(x[a.link_seq_no] for a in v.outgoing_link_list if a.link_type not in ['vv','vp'])
                -gb.quicksum(x[a.link_seq_no] for a in v.incoming_link_list if a.link_type not in ['vv','vp']))
                == 0,name="MC1[%d]"%(num))                
                num+=1
        
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction      
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        # tpp=tp+sec.run_time
                        if tp<param.train_latest_time[run_dir,from_node_id]+1:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                
                if len(temp_safe_node)>0:
                    self.__origin_model.addConstr((gb.quicksum(self.z[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            <= 1,name="MC2[%d,%d,%d]"%(from_node_id,t,run_dir))

                if len(temp_safe_node_max)>0:
                    self.__origin_model.addConstr((gb.quicksum(self.z[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node_max
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            >= 1,name="MC21[%d,%d,%d]"%(from_node_id,t,run_dir))          

                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                
                self.__origin_model.addConstr(gb.quicksum(self.z[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                       if link.link_type in ['ur','dr']
                                                       for l in param.level_comosition) <= 1,name="MC4[%d,%d,%d]"%(from_node_id,run_dir,t))
                
                
                self.__origin_model.addConstr(gb.quicksum(self.z[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1,name="MC41[%d,%d,%d]"%(from_node_id,run_dir,t))
              
            for link_seq_no in (network.station_arc_run[from_node_id,run_dir] + network.uncouple_arc[from_node_id,run_dir] + network.couple_arc[from_node_id,run_dir]):
                self.__origin_model.addConstr(gb.quicksum(l*self.z[link_seq_no,l] for l in param.level_comosition) == x[link_seq_no],name="MC3[%d]"%(link_seq_no))             
                     
        
        for a in network.link_list:
            if a.link_type=='vt':
                link_seq_no=a.link_seq_no
                from_node_id=a.from_node_id
                to_node_id=a.to_node_id
                run_dir=a.link_direction
                if a.from_node_id<0:
                    self.__origin_model.addConstr(x[link_seq_no] == network.init_unit[run_dir,to_node_id],name="MC5[%d]"%(link_seq_no))             
                else:
                    self.__origin_model.addConstr(x[link_seq_no] >= network.end_unit[run_dir,from_node_id],name="MC5[%d]"%(link_seq_no))             
            
            elif a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no 
                self.__origin_model.addConstr(x[link_seq_no] >=
                gb.quicksum(x[temp_link.link_seq_no]+0.5*gb.quicksum(self.z[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no))
            
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                self.__origin_model.addConstr(x[link_seq_no] <=
                gb.quicksum(x[temp_link.link_seq_no]-0.5*gb.quicksum(self.z[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no)) 
        
        #passenger constraints
        num=0
        for w in demand.OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2
            #passenger flow balance-starting
            index_ori=(-s-100,-s-100,-s-100,-s-100)
            node_seq_no=network.node_index_to_no_dict[index_ori]
            self.__origin_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list if a.to_node_id==s if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d]"%(num))
            num+=1
            
            #passenger flow balance-starting
            index_des=(-sp-100,-sp-100,-sp-100,-sp-100)
            node_seq_no=network.node_index_to_no_dict[index_des]
            self.__origin_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list if a.from_node_id==sp if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d]"%(num))
            num+=1
            
            #passenger flow balance-inter
            for v in network.node_list:
                if v.node_id==s and v.node_attr==1 and v.node_direction==run_dir:
                    self.__origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['vp']                                                    
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                
                elif v.node_id==sp and (v.node_attr==1 or v.node_attr==3) and v.node_direction==run_dir:
                    self.__origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                  if a.link_type in ['vp']                                                                                    
                                                                                  if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','cod','ucd']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                    
                elif (s<v.node_id<sp) or (sp<v.node_id<s):
                    # print(v.node_id)
                    self.__origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir))
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir)
                    == 0,name="MC61[%d]"%(num))
                    num+=1
        
            #cumulative constraints            
            from_node_id=s
            to_node_id=s+1 if run_dir==1 else s-1
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                self.__origin_model.addConstr(gb.quicksum(y[w,link_no] for link_no in network.ori_arc_run[w,t]
                            if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id]
                ) <= demand.demand_accum[w,t],name="MC7[%d,%d,%d]"%(w[0],w[1],t))             
        
        
        #new constraint
        for s in network.OD_station[w]:
            if s!=w[1]:
                for t in range(param.earliest_time[w,s],param.latest_time[w,s]+1):                        
                    index=(s,t,run_dir,1)
                    node_seq_no=network.node_index_to_no_dict[index]
                    self.__origin_model.addConstr(self.b_variable[w,s,t]==
                        gb.quicksum(y[w,link.link_seq_no] for link in network.node_list[node_seq_no].outgoing_link_list
                                                          if link.link_type in ['ur','dr'])
                    ,name="MC71[%d,%d,%d,%d]"%(w[0],w[1],s,t))
        
        
        
        #passenger arc capacity
        for sec in network.section_list:
            s=sec.from_node_id
            run_dir=sec.run_direction
            for link_seq_no in (network.station_arc_run[s,run_dir] + network.uncouple_arc[s,run_dir] + network.couple_arc[s,run_dir]): 
            # for link_seq_no in (network.station_arc_run[s,run_dir]):                
                # print(network.link_list[link_seq_no].link_type,link_seq_no)
                # input()
                self.__origin_model.addConstr(gb.quicksum(y[w,link_seq_no] for w in sec.belong_OD_list
                if param.earliest_time[w,network.link_list[link_seq_no].from_node_id]<=network.link_list[link_seq_no].start_time<=param.latest_time[w,network.link_list[link_seq_no].from_node_id])
                <= x[link_seq_no]*param.single_cap,name="MC8[%d]"%(link_seq_no))
        
        
            # self.__origin_model.addConstr(gb.quicksum(self.z[link_no,l] for link_no in network.station_arc_run[s,run_dir] 
                                                                   # for l in param.level_comosition)
                # >=8,name="MC81[%d]"%(sec.section_id))
            
            # self.__origin_model.addConstr(gb.quicksum(self.z[link_no,l] for link_no in network.station_arc_run[s,run_dir] 
                                                                   # for l in param.level_comosition)
                # <=11,name="MC82[%d]"%(sec.section_id))
        
        for w in demand.OD_list:
        # for w in param.key_OD_list:
            if w not in vad_ine_list:
                s=w[0]
                sp=w[1]
                run_dir=1 if s<sp else 2
                step=1 if run_dir==1 else -1
                
                val_obj=0
                temp_link={}
                tt_sec_dis=0
                for sb in range(s,sp,step):
                    sec=network.sec_index_to_no_dict[run_dir,sb]
                    tt_sec_dis+=sec.sec_dis
                    for link_no in network.station_arc_run[sb,run_dir]:
                        if param.earliest_time[w,sb]<=network.link_list[link_no].start_time<=param.latest_time[w,sb]:
                            temp_link[link_no]=sec.sec_dis
                            # for l in param.level_comosition:
                                # val_obj+=param.weight_train*sec.sec_dis*z_var[link_no,l]*param.cost_composition[l]  
              
                temp_OD=[]
                for wp in demand.OD_list:
                    p_run_dir=1 if wp[0]<wp[1] else 2
                    flag_ture=False
                    if wp[0]==w[0] and wp[1]>=w[1] and p_run_dir==1 and p_run_dir==run_dir:
                        flag_ture=True
                        temp_OD.append(wp)
                    elif wp[0]==w[0] and wp[1]<=w[1] and p_run_dir==2 and p_run_dir==run_dir:
                        flag_ture=True
                        temp_OD.append(wp)
                        
                    if flag_ture==True:
                        num1=0                     
                        for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1):
                            num=0
                            # for tp in range(param.earliest_time[wp,s],t+1):                            
                                # num+=b_var[wp,wp[0],tp]
                            
                            # val_obj+=param.weight_pax*param.wait_pax_cost*(demand.demand_accum[wp,t]-num)
                                               
                            # num1 += b_var[wp,wp[0],t]
                            
                         
                        # val_obj+=param.weight_pax*param.vitual_pax_cost*(max(0,demand.demand_OD[wp]-num1))
               
                # print(w,val_obj)
                # print(object_INI.lower_bound_OD[w])
                # input()
                
                self.__origin_model.addConstr(param.weight_train*(
                gb.quicksum(temp_link[link_no]*self.z[link_no,l]*param.cost_composition[l]                                                   
                                        for link_no in temp_link.keys()                                    
                                        for l in param.level_comosition))
                +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[wp,t]-gb.quicksum(self.b_variable[wp,wp[0],tp] for tp in range(param.earliest_time[wp,wp[0]],t+1)))
                                                                    for wp in temp_OD
                                                                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1))
                +param.weight_pax*param.vitual_pax_cost*1*gb.quicksum((demand.demand_OD[wp]-gb.quicksum(self.b_variable[wp,wp[0],t]
                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1)))for wp in temp_OD)
                >=object_INI.lower_bound_OD[w]
                )

                self.__origin_model.addConstr(param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[wp,t]-gb.quicksum(self.b_variable[wp,wp[0],tp] for tp in range(param.earliest_time[wp,wp[0]],t+1)))
                                                                    for wp in temp_OD
                                                                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1))
                +param.weight_pax*param.vitual_pax_cost*1*gb.quicksum((demand.demand_OD[wp]-gb.quicksum(self.b_variable[wp,wp[0],t]
                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1)))for wp in temp_OD)
                >=object_INI.lower_bound_OD_waittime[w]
                )                
        
        
        
        
        #objective function
        self.__origin_model.addConstr(gb.quicksum(sec.sec_dis*self.z[link_no,l]*param.cost_composition[l] 
                                                    for sec in network.section_list
                                                        for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                            for l in param.level_comosition)                      
                                    +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]                                    
                                    for s in range(param.num_station)
                                        for run_dir in [1,2]
                                            for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir])))
                                    == obj_train,name="MCA")
            
        self.__origin_model.addConstr(gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(y[w,link_no] for link_no in network.ori_arc_run[w,t]
                                                if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id]))
                                                    for w in demand.OD_list
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))*param.wait_pax_cost                     
                                +gb.quicksum(y[w_p,network.vir_arc_pax[w_p]]for w_p in demand.OD_list)*param.vitual_pax_cost                           
                                     == obj_pax,name="MCB")

        self.__origin_model.setObjective(param.weight_pax*obj_pax+param.weight_train*obj_train,gb.GRB.MINIMIZE)
        #
        
        
        # for key in object_INI.last_link:
            # if key in self.z.keys():
                # self.z[key].ub=0
        
        
        self.__origin_model.update()
      
    

    def process(self):
        
        self.origin_model()
        self.__origin_model.Params.TimeLimit=5400
        self.__origin_model.optimize()
        
        print("finish __origin_model loading!")
        
        # self.__origin_model.Params.TimeLimit=1000
        # self.__origin_model.Params.BranchDir=-1
        # self.__origin_model.Params.lazyConstraints = 1        
        # self.__origin_model.optimize(mycallback)
        
        # self.__origin_model.computeIIS()
        # self.__origin_model.write("xxx33.ilp") 
        # print("模型MP不可行！！！")
        # input()
        
        Output().output_result(self.__origin_model,"G_M1")
        
        print("B.cuts.{}, O.cuts.{},initial.cuts.{}".format(num_B_cuts,num_O_cuts,len(demand.OD_list)))
        gap=100*(self.UB-self.LB)/self.UB    
        print("UB is {}, LB is {}, gap is {}.".format(self.UB,self.LB,gap))
        input() 

            
num_B_cuts=0
num_O_cuts=0
num_Gap_display=0
exp_node_list=[]
unit_period=140
vad_ine_list=[]
def mycallback(model, where): #运行时请去掉M0 变为 mycallback
    global num_B_cuts,num_Gap_display,unit_period
    global exp_node_list,vad_ine_list
    # print(where)
    # input()
    if where == gb.GRB.Callback.MIPSOL or where == gb.GRB.Callback.MIPNODE:        
        flag_stop=False
        b_var=None
        z_var=None
        theta_var=None
        vit_time=None
        wait_time=None
        obj_train=None
        flag=0
           
            
        if where == gb.GRB.Callback.MIPNODE and model.cbGet(gb.GRB.Callback.MIPNODE_STATUS)==2: #节点获得松弛解，非整数可行解
          
            b_var = model.cbGetNodeRel(object_G_M0_H.b_variable)
            z_var = model.cbGetNodeRel(object_G_M0_H.z)
                 

            
            num_node=model.cbGet(gb.GRB.Callback.MIPNODE_NODCNT)  
            
            
            if num_node<1 or num_node%10==0:               
                add_valid_inequality_OD_G_M0_H(model,z_var,b_var)
            
            
            if model.cbGet(gb.GRB.Callback.RUNTIME)>5400:
                model.terminate()
          


def add_valid_inequality_OD_G_M0_H(model,z_var,b_var): 
    for w in demand.OD_list:
    # for w in param.key_OD_list:
        if w not in vad_ine_list:
            s=w[0]
            sp=w[1]
            run_dir=1 if s<sp else 2
            step=1 if run_dir==1 else -1
            
            val_obj=0
            temp_link={}
            tt_sec_dis=0
            for sb in range(s,sp,step):
                sec=network.sec_index_to_no_dict[run_dir,sb]
                tt_sec_dis+=sec.sec_dis
                for link_no in network.station_arc_run[sb,run_dir]:
                    if param.earliest_time[w,sb]<=network.link_list[link_no].start_time<=param.latest_time[w,sb]:
                        temp_link[link_no]=sec.sec_dis
                        for l in param.level_comosition:
                            val_obj+=param.weight_train*sec.sec_dis*z_var[link_no,l]*param.cost_composition[l]  
          
            temp_OD=[]
            for wp in demand.OD_list:
                p_run_dir=1 if wp[0]<wp[1] else 2
                flag_ture=False
                if wp[0]==w[0] and wp[1]>=w[1] and p_run_dir==1 and p_run_dir==run_dir:
                    flag_ture=True
                    temp_OD.append(wp)
                elif wp[0]==w[0] and wp[1]<=w[1] and p_run_dir==2 and p_run_dir==run_dir:
                    flag_ture=True
                    temp_OD.append(wp)
                    
                if flag_ture==True:
                    num1=0                     
                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1):
                        num=0
                        for tp in range(param.earliest_time[wp,s],t+1):                            
                            num+=b_var[wp,wp[0],tp]
                        
                        val_obj+=param.weight_pax*param.wait_pax_cost*(demand.demand_accum[wp,t]-num)
                                           
                        num1 += b_var[wp,wp[0],t]
                        
                     
                    val_obj+=param.weight_pax*param.vitual_pax_cost*(max(0,demand.demand_OD[wp]-num1))
           
            # print(w,val_obj)
            # print(object_INI.lower_bound_OD[w])
            # input()
            
            if val_obj<object_INI.lower_bound_OD[w]-1:
                model.cbLazy(param.weight_train*(
                gb.quicksum(temp_link[link_no]*object_G_M0_H.z[link_no,l]*param.cost_composition[l]                                                   
                                        for link_no in temp_link.keys()                                    
                                        for l in param.level_comosition))
                +param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[wp,t]-gb.quicksum(object_G_M0_H.b_variable[wp,wp[0],tp] for tp in range(param.earliest_time[wp,wp[0]],t+1)))
                                                                    for wp in temp_OD
                                                                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1))
                +param.weight_pax*param.vitual_pax_cost*1*gb.quicksum((demand.demand_OD[wp]-gb.quicksum(object_G_M0_H.b_variable[wp,wp[0],t]
                    for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1)))for wp in temp_OD)
                >=object_INI.lower_bound_OD[w]
                )
                
                # model.cbLazy(param.weight_pax*param.wait_pax_cost*1*gb.quicksum((demand.demand_accum[wp,t]-gb.quicksum(object_G_M0_H.b_variable[wp,wp[0],tp] for tp in range(param.earliest_time[wp,wp[0]],t+1)))
                                                                    # for wp in temp_OD
                                                                    # for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1))
                # +param.weight_pax*param.vitual_pax_cost*1*gb.quicksum((demand.demand_OD[wp]-gb.quicksum(object_G_M0_H.b_variable[wp,wp[0],t]
                    # for t in range(param.earliest_time[wp,s],param.latest_time[wp,s]+1)))for wp in temp_OD)
                # >=object_INI.lower_bound_OD_waittime[w]
                # )
                
                vad_ine_list.append(w)
            
        
class OriginModel_to_Gurobi:
    def __init__(self):
        self.__origin_model = gb.Model("origin_model")
        
    def origin_model(self):
        obj_train=self.__origin_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_train')
        obj_pax=self.__origin_model.addVar(lb=-gb.GRB.INFINITY,ub=gb.GRB.INFINITY,vtype=gb.GRB.CONTINUOUS,name='obj_pax')
        x=gb.tupledict()
        y=gb.tupledict()
        z=gb.tupledict()
        for a in network.link_list:
            #train-related varibles
            if a.link_type not in ['vp','vv']:
                x[a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=a.link_cap,vtype=gb.GRB.INTEGER,name='x[%d]'%(a.link_seq_no))
                if a.link_type in ['ur','dr','cod','ucd']:        
                    
                    if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                        x[a.link_seq_no].ub=0
                    
                    for l in param.level_comosition:
                        z[a.link_seq_no,l]=self.__origin_model.addVar(lb=0,ub=1,vtype=gb.GRB.BINARY,name='z[%d,%d]'%(a.link_seq_no,l))
                        
                        if param.train_early_time[a.link_direction,a.from_node_id]>a.from_time or a.from_time>param.train_latest_time[a.link_direction,a.from_node_id]:
                            z[a.link_seq_no,l].ub=0
         
            #pax-related varibles
            if a.link_type not in ['vt','tud','tdu','idl','ucr']:
                for w in demand.OD_list:
                    run_dir=1 if w[0]<w[1] else 2 
                    
                    if a.link_type=='vv' and a.from_node_id==w[0] and a.to_node_id==w[1]:
                        y[w,a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                    elif a.link_type=='vp' and (a.from_node_id==w[1] or a.to_node_id==w[0]) and a.link_direction==run_dir:
                        y[w,a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))
                    
                    elif a.link_type not in ['vv','vp'] and a.link_direction==run_dir:                        
                        if (w[0]<=a.from_node_id<=a.to_node_id<=w[1] or w[1]<=a.to_node_id<=a.from_node_id<=w[0]) and param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]:
                            if a.link_type in ['ur','dr']:                            
                                y[w,a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        
                            if a.link_type in ['ucd','cod']:
                                y[w,a.link_seq_no]=self.__origin_model.addVar(lb=0,ub=demand.demand_OD[w],vtype=gb.GRB.CONTINUOUS,name='y[%d,%d,%d]'%(w[0],w[1],a.link_seq_no))                        
                        
                        # if w[1]<=a.to_node_id<a.from_node_id<=w[0]:
                            # print(w,a.to_node_id,a.from_node_id,w[0],w[1])
                            # input()
                            
        for t in range(param.max_time-param.couple_time,param.max_time):
            for s in network.turnback_station_list:
                if s not in [0,param.num_station-1]:
                    for run_dir in [1,2]:
                        index=(s,t,run_dir,2)
                        node_seq=network.node_index_to_no_dict[index]
                        for link in network.node_list[node_seq].incoming_link_list:
                            if link.link_type in ['dr','ur']:
                                x[link.link_seq_no].ub=0                    
                            
        #add constraints
        #train flow balance-starting outgoing
        node_seq_no=network.node_index_to_no_dict[(-1,-1,-1,-1)]
        self.__origin_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list) == param.max_unit,name="MC1[-1]")
        
        #train flow balance-ending ingoing
        node_seq_no=network.node_index_to_no_dict[(-2,-2,-2,-2)]
        self.__origin_model.addConstr(gb.quicksum(x[a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list) == param.max_unit,name="MC1[-2]")
        
        #train flow balance-inter node
        num=0
        for v in network.node_list:
            # print(v.node_id)
            if v.node_id>=0:
                self.__origin_model.addConstr((gb.quicksum(x[a.link_seq_no] for a in v.outgoing_link_list if a.link_type not in ['vv','vp'])
                -gb.quicksum(x[a.link_seq_no] for a in v.incoming_link_list if a.link_type not in ['vv','vp']))
                == 0,name="MC1[%d]"%(num))                
                num+=1
        
        # safe interval constraints
        for sec in network.section_list:   
            run_dir=sec.run_direction      
            from_node_id=sec.from_node_id
            to_node_id=sec.to_node_id
            for t in range(param.train_latest_time[run_dir,from_node_id]+1):                
                temp_safe_node=[]
                for tp in range(t,t+param.safe_interval):                    
                    # tpp=tp+sec.run_time
                    if tp<param.train_latest_time[run_dir,from_node_id]+1:
                        # to_index=to_node_id*param.len_time+tpp*10+run_dir
                        from_index=(from_node_id,tp,run_dir,1)
                        node_seq_no=network.node_index_to_no_dict[from_index]
                        temp_safe_node.append(node_seq_no)
                
                temp_safe_node_max=[]
                if param.train_early_time[run_dir,from_node_id]<=t<param.train_latest_time[run_dir,from_node_id]-param.max_interval:
                    for tp in range(t,t+param.max_interval):                    
                        # tpp=tp+sec.run_time
                        if tp<param.train_latest_time[run_dir,from_node_id]+1:
                            # to_index=to_node_id*param.len_time+tpp*10+run_dir
                            from_index=(from_node_id,tp,run_dir,1)
                            node_seq_no=network.node_index_to_no_dict[from_index]
                            temp_safe_node_max.append(node_seq_no)
                
                if len(temp_safe_node)>0:
                    self.__origin_model.addConstr((gb.quicksum(z[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            <= 1,name="MC2[%d,%d,%d]"%(from_node_id,t,run_dir))

                if len(temp_safe_node_max)>0:
                    self.__origin_model.addConstr((gb.quicksum(z[link.link_seq_no,l] for l in param.level_comosition for node_seq_no in temp_safe_node_max
                                                                                  for link in network.node_list[node_seq_no].outgoing_link_list
                                                                                      if link.link_type in ['ur','dr']))
                            >= 1,name="MC21[%d,%d,%d]"%(from_node_id,t,run_dir))          

                node_index=(from_node_id,t,run_dir,1)
                node_seq_no=network.node_index_to_no_dict[node_index]
                
                self.__origin_model.addConstr(gb.quicksum(z[link.link_seq_no,l] for link in network.node_list[node_seq_no].outgoing_link_list
                                                       if link.link_type in ['ur','dr']
                                                       for l in param.level_comosition) <= 1,name="MC4[%d,%d,%d]"%(from_node_id,run_dir,t))
                
                
                self.__origin_model.addConstr(gb.quicksum(z[link.link_seq_no,l] for link in network.node_list[node_seq_no].incoming_link_list
                                                           if link.link_type in ['ur','dr','cod','ucd']
                                                           for l in param.level_comosition) <= 1,name="MC41[%d,%d,%d]"%(from_node_id,run_dir,t))
              
            for link_seq_no in (network.station_arc_run[from_node_id,run_dir] + network.uncouple_arc[from_node_id,run_dir] + network.couple_arc[from_node_id,run_dir]):
                self.__origin_model.addConstr(gb.quicksum(l*z[link_seq_no,l] for l in param.level_comosition) == x[link_seq_no],name="MC3[%d]"%(link_seq_no))             
                     
        
        for a in network.link_list:
            if a.link_type=='vt':
                link_seq_no=a.link_seq_no
                from_node_id=a.from_node_id
                to_node_id=a.to_node_id
                run_dir=a.link_direction
                if a.from_node_id<0:
                    self.__origin_model.addConstr(x[link_seq_no] == network.init_unit[run_dir,to_node_id],name="MC5[%d]"%(link_seq_no))             
                else:
                    self.__origin_model.addConstr(x[link_seq_no] >= network.end_unit[run_dir,from_node_id],name="MC5[%d]"%(link_seq_no))             
            
            elif a.link_type=='cod':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no 
                self.__origin_model.addConstr(x[link_seq_no] >=
                gb.quicksum(x[temp_link.link_seq_no]+0.5*gb.quicksum(z[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no))
            
            elif a.link_type=='ucd':
                link_seq_no=a.link_seq_no
                from_seq_no=a.from_node_seq_no
                self.__origin_model.addConstr(x[link_seq_no] <=
                gb.quicksum(x[temp_link.link_seq_no]-0.5*gb.quicksum(z[temp_link.link_seq_no,l] for l in param.level_comosition) 
                        for temp_link in network.node_list[from_seq_no].incoming_link_list
                        if temp_link.link_type in ['ur','dr']),name="MC51[%d]"%(link_seq_no)) 
        
        #passenger constraints
        num=0
        for w in demand.OD_list:
            s=w[0];sp=w[1]
            run_dir=1 if s<sp else 2
            #passenger flow balance-starting
            index_ori=(-s-100,-s-100,-s-100,-s-100)
            node_seq_no=network.node_index_to_no_dict[index_ori]
            self.__origin_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].outgoing_link_list if a.to_node_id==s if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d]"%(num))
            num+=1
            
            #passenger flow balance-starting
            index_des=(-sp-100,-sp-100,-sp-100,-sp-100)
            node_seq_no=network.node_index_to_no_dict[index_des]
            self.__origin_model.addConstr(gb.quicksum(y[w,a.link_seq_no] for a in network.node_list[node_seq_no].incoming_link_list if a.from_node_id==sp if a.link_direction==run_dir) + y[w,network.vir_arc_pax[w]] == demand.demand_OD[w],name="MC6[%d]"%(num))
            num+=1
            
            #passenger flow balance-inter
            for v in network.node_list:
                if v.node_id==s and v.node_attr==1 and v.node_direction==run_dir:
                    self.__origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['vp']                                                    
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                
                elif v.node_id==sp and (v.node_attr==1 or v.node_attr==3) and v.node_direction==run_dir:
                    self.__origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                  if a.link_type in ['vp']                                                                                    
                                                                                  if a.link_direction==run_dir)
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','cod','ucd']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir))
                    == 0,name="MC6[%d]"%(num))
                    num+=1
                    
                elif (s<v.node_id<sp) or (sp<v.node_id<s):
                    # print(v.node_id)
                    self.__origin_model.addConstr((gb.quicksum(y[w,a.link_seq_no] for a in v.outgoing_link_list
                                                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                                                    if a.link_direction==run_dir))
                    -gb.quicksum(y[w,a.link_seq_no] for a in v.incoming_link_list
                                                    if a.link_type in ['ur','dr','ucd','cod']
                                                    if param.earliest_time[w,a.from_node_id]<=a.start_time<=param.latest_time[w,a.from_node_id]
                                                    if a.link_direction==run_dir)
                    == 0,name="MC61[%d]"%(num))
                    num+=1
        
            #cumulative constraints            
            from_node_id=s
            to_node_id=s+1 if run_dir==1 else s-1
            for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1):
                self.__origin_model.addConstr(gb.quicksum(y[w,link_no] for link_no in network.ori_arc_run[w,t]
                            if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id]
                ) <= demand.demand_accum[w,t],name="MC7[%d,%d,%d]"%(w[0],w[1],t))             
        
        #passenger arc capacity
        for sec in network.section_list:
            s=sec.from_node_id
            run_dir=sec.run_direction
            for link_seq_no in (network.station_arc_run[s,run_dir] + network.uncouple_arc[s,run_dir] + network.couple_arc[s,run_dir]): 
            # for link_seq_no in (network.station_arc_run[s,run_dir]):                
                # print(network.link_list[link_seq_no].link_type,link_seq_no)
                # input()
                self.__origin_model.addConstr(gb.quicksum(y[w,link_seq_no] for w in sec.belong_OD_list
                if param.earliest_time[w,network.link_list[link_seq_no].from_node_id]<=network.link_list[link_seq_no].start_time<=param.latest_time[w,network.link_list[link_seq_no].from_node_id])
                <= x[link_seq_no]*param.single_cap,name="MC8[%d]"%(link_seq_no))
        
        
            # self.__origin_model.addConstr(gb.quicksum(z[link_no,l] for link_no in network.station_arc_run[s,run_dir] 
                                                                   # for l in param.level_comosition)
                # >=8,name="MC81[%d]"%(sec.section_id))
            
            # self.__origin_model.addConstr(gb.quicksum(z[link_no,l] for link_no in network.station_arc_run[s,run_dir] 
                                                                   # for l in param.level_comosition)
                # <=11,name="MC82[%d]"%(sec.section_id))
        
        #objective function
        self.__origin_model.addConstr(gb.quicksum(sec.sec_dis*z[link_no,l]*param.cost_composition[l] 
                                                    for sec in network.section_list
                                                        for link_no in network.station_arc_run[sec.from_node_id,sec.run_direction]
                                                            for l in param.level_comosition)                      
                                    +param.weight_sta_opera*(gb.quicksum(network.link_list[link_no].link_cost*x[link_no]                                    
                                    for s in range(param.num_station)
                                        for run_dir in [1,2]
                                            for link_no in (network.transfer_arc[s,run_dir]+network.uncouple_arc[s,run_dir]+network.couple_arc[s,run_dir]+network.return_arc[s,run_dir])))
                                    == obj_train,name="MCA")
            
        self.__origin_model.addConstr(gb.quicksum((demand.demand_accum[w,t]-gb.quicksum(y[w,link_no] for link_no in network.ori_arc_run[w,t]
                                                if param.earliest_time[w,network.link_list[link_no].from_node_id]<=network.link_list[link_no].start_time<=param.latest_time[w,network.link_list[link_no].from_node_id]))
                                                    for w in demand.OD_list
                                                        for t in range(param.earliest_time[w,w[0]],param.latest_time[w,w[0]]+1))*param.wait_pax_cost                     
                                +gb.quicksum(y[w_p,network.vir_arc_pax[w_p]]for w_p in demand.OD_list)*param.vitual_pax_cost                           
                                     == obj_pax,name="MCB")

        self.__origin_model.setObjective(param.weight_pax*obj_pax+param.weight_train*obj_train,gb.GRB.MINIMIZE)
        #
        
        
        # for key in object_INI.last_link:
            # if key in z.keys():
                # z[key].ub=0
        
        
        self.__origin_model.update()
        # self.__origin_model.Params.MIPGap=0.002
        self.__origin_model.Params.TimeLimit=5400
        
        # self.__origin_model.write("xxx33.lp")
        # input()
        
        self.__origin_model.optimize()
        
        print(param.weight_pax*obj_pax.x,param.weight_train*obj_train.x)
        
        # print(x[919].x)
        # input()
        
        # self.__origin_model.computeIIS()
        # self.__origin_model.write("xxx33.ilp")
        # print("model,xxx333")
        
        for sec in network.section_list:
            s=sec.from_node_id
            run_dir=sec.run_direction
            for link_seq_no in (network.uncouple_arc[s,run_dir] + network.couple_arc[s,run_dir]):                
                # for link_seq_no in (network.station_arc_run[s,run_dir]): #仅仅运行弧是有问题的            
                # print(network.link_list[link_seq_no].link_type,link_seq_no)
                    # input()
                temp1=0
                for w in sec.belong_OD_list:
                    if (param.earliest_time[w,network.link_list[link_seq_no].from_node_id]<=network.link_list[link_seq_no].start_time<=param.latest_time[w,network.link_list[link_seq_no].from_node_id]):
                        temp1+=y[w,link_seq_no].x 
                
                temp2=x[link_seq_no].x*param.single_cap
                
                if temp2<temp1:
                    print("违背能力检测：",temp2,temp1,s,link_seq_no)
                    for w in sec.belong_OD_list:
                        if (param.earliest_time[w,network.link_list[link_seq_no].from_node_id]<=network.link_list[link_seq_no].start_time<=param.latest_time[w,network.link_list[link_seq_no].from_node_id]):
                            if y[w,link_seq_no].x>0:
                                print(w,link_seq_no,y[w,link_seq_no].x)
                    input()
           
     
        print("pax obj:{},train obj:{}".format(obj_pax.x,obj_train.x))
        Output().output_result(self.__origin_model,"G_M1")
        input()
    


# class Benders_multcus:
    # def __init__(self):
        
# class Benders_singlecus:
    # def __init__(self):

class Output:
    def __init__(self):
        self.opt_model=None
    def output_result(self,model,file_name):
        self.opt_model=model
        
        total_unit_travel_time=0
        up_num_unit=0
        down_num_unit=0
        up_ave_service=0
        down_ave_service=0
        
        with open(output_dir + "/result_"+file_name+".csv", "w", newline="") as fp:
            writer = csv.writer(fp)        
        
            temp=['varName','type','from_node','to_node','from_time','to_time','from_seq_no','to_seq_no','value','OD']
            writer.writerow(temp)        
        
            for var in self.opt_model.getVars():
                temp=[]
                vName=var.varName            
                if vName[0]=='x':
                    if var.x>0.0001:
                        vName=vName[2:-1].split(',')
                        vName = list(map(int,vName))
                        link_seq_no=vName[0]
                        # print(vName,var.x,link_seq_no)
                        temp.append('x')
                        temp.append(network.link_list[link_seq_no].link_type)
                        temp.append(network.link_list[link_seq_no].from_node_id)
                        temp.append(network.link_list[link_seq_no].to_node_id)
                        from_node_seq_no=network.link_list[link_seq_no].from_node_seq_no
                        to_node_seq_no=network.link_list[link_seq_no].to_node_seq_no                        
                        temp.append(network.node_list[from_node_seq_no].node_time)
                        temp.append(network.node_list[to_node_seq_no].node_time)
                        temp.append(from_node_seq_no)
                        temp.append(to_node_seq_no)
                        temp.append(var.x)
                        
                        # if (network.link_list[link_seq_no].from_node_id==1 and 
                            # network.link_list[link_seq_no].to_node_id==2 and
                            # network.node_list[from_node_seq_no].node_time==26 and 
                            # network.node_list[to_node_seq_no].node_time==29):
                            # print(var.varName,var.x)
                            # input()
                        
                        if network.link_list[link_seq_no].link_type in ['ur','dr']:
                            total_unit_travel_time+=round(var.x)*network.link_list[link_seq_no].link_travel_time
                            if network.link_list[link_seq_no].link_direction == 1:
                                up_ave_service+=1
                                up_num_unit+=round(var.x)
                            elif network.link_list[link_seq_no].link_direction == 2:
                                down_ave_service+=1
                                down_num_unit+=round(var.x)
                        
                        # input()
                elif vName[0]=='y':
                    if var.x>0.0001:
                        vName=vName[2:-1].split(',')
                        vName = list(map(int,vName))
                        link_seq_no=vName[2]
                        # print(vName,var.x,link_seq_no)
                        # input()
                        temp.append('y')
                        temp.append(network.link_list[link_seq_no].link_type)                        
                        temp.append(network.link_list[link_seq_no].from_node_id)
                        temp.append(network.link_list[link_seq_no].to_node_id)
                        from_node_seq_no=network.link_list[link_seq_no].from_node_seq_no
                        to_node_seq_no=network.link_list[link_seq_no].to_node_seq_no
                        temp.append(network.node_list[from_node_seq_no].node_time)
                        temp.append(network.node_list[to_node_seq_no].node_time)
                        temp.append(from_node_seq_no)
                        temp.append(to_node_seq_no)                        
                        temp.append(var.x)
                        temp.append((vName[0],vName[1]))
                        # input()
                
                if len(temp)>0:
                    writer.writerow(temp) 
        
        print("total_unit_travel_time.{}".format(total_unit_travel_time))
        print("total_num_service.{},up.{},down.{}".format(up_ave_service+down_ave_service,up_ave_service,down_ave_service))
        print("ave_service_up.{},ave_service_down.{}".format(up_ave_service/11,down_ave_service/11))        
        print("total_num_unit.{},up.{},down.{}".format(up_num_unit+down_num_unit,up_num_unit,down_num_unit))
        print("ave_num_unit_up.{},ave_num_unit_down.{}".format(up_num_unit/up_ave_service,down_num_unit/down_ave_service))
        
        
        print("output successfull!")
        #input()

    def output_result_for_BAC(self,x_value):
        
        with open(output_dir + "/result_BC.csv", "w", newline="") as fp:
            writer = csv.writer(fp)
        
            temp=['varName','type','from_node','to_node','from_time','to_time','from_seq_no','to_seq_no','value']
            writer.writerow(temp)        
        
            for link_seq_no in x_value.keys():
                temp=[]              
                val=x_value[link_seq_no]
                temp.append('x')
                temp.append(network.link_list[link_seq_no].link_type)
                temp.append(network.link_list[link_seq_no].from_node_id)
                temp.append(network.link_list[link_seq_no].to_node_id)
                from_node_seq_no=network.link_list[link_seq_no].from_node_seq_no
                to_node_seq_no=network.link_list[link_seq_no].to_node_seq_no                        
                temp.append(network.node_list[from_node_seq_no].node_time)
                temp.append(network.node_list[to_node_seq_no].node_time)
                temp.append(from_node_seq_no)
                temp.append(to_node_seq_no)
                temp.append(val)
                # input()
                
                if len(temp)>0:
                    writer.writerow(temp) 
        print("output successfull!")
        input()
          
def main():    #main function
    global demand,param,network,output,object_INI,object_BAC,object_BAC_M0,object_G_M0_H,input_dir,output_dir
    
    # model = gb.read("xxx33.lp")
    # model.Params.InfUnbdInfo = 1
    # model.optimize()
    
    # input_dir = './VirtualCouple/ExpComparison/input'
    # output_dir='./VirtualCouple/ExpComparison/output'   
    
    input_dir = './VirtualCouple/Explarge/input'
    output_dir='./VirtualCouple/Explarge/output' 
    
    demand,param,network = read_network(input_dir)
    
    object_INI=WarmStartInitialSol()
    
    # OriginModel_to_Gurobi().origin_model()
    # input()
    
    object_INI.process()    

    
    # object_BAC=Benders_BAC_multcuts()
    # object_BAC.process()
    
    # object_BAC_M0=Benders_BAC_onecuts_M0()
    # object_BAC_M0.process()  
    
    object_G_M0_H=Gurobi_Callback_M0()
    object_G_M0_H.process()  
    
  
    print("Finish!!!")
    input()
    
    
 
if __name__ == "__main__":
    main()
