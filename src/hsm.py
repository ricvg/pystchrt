'''
Hierarchical State Machine
'''
import fsm


class Event(fsm.Event):
    pass


class TransitionWithGuardAndAction(fsm.TransitionWithGuardAndAction):
    pass


class TransitionWithGuard(fsm.TransitionWithGuard):
    pass


class TransitionWithAction(fsm.TransitionWithAction):
    pass


class Transition(fsm.Transition):
    pass


class ActivityWithGuard(fsm.ActivityWithGuard):
    pass


class Activity(fsm.Activity):
    pass


class TransitionAndActivityResult(fsm.TransitionAndActivityResult):
    pass


class SimpleState(fsm.State):

    def __init__(self):
        fsm.State.__init__(self)
        self.parent = None
    
    def process_event(self, event):
        trans_and_act_res = fsm.State.process_event(self, event)
        if not trans_and_act_res.did_act_or_requested_transition() and self.has_parent():
            return self.parent.process_event(event)
        else:
            return trans_and_act_res
    
    def start(self):
        return TransitionAndActivityResult.buildUntriggeredActivityAndTransition()
    
    def stop(self):
        return TransitionAndActivityResult.buildUntriggeredActivityAndTransition()
    
    def has_parent(self):
        return None != self.parent

    def get_parent_stack(self):
        stack = []
        state = self
        while True:
            stack.append(state)
            
            if not state.has_parent():
                break

            state = state.parent
        stack.reverse()
        return stack

    def is_parent(self, other):
        if self.parent == None:
            return False
    
        if self.parent == other:
            return True
        else:
            return self.parent.is_parent(other)

    def __contains__(self, child):
        return False


class CompositeState(fsm.FSM, SimpleState):
    
    class InitialState(SimpleState, fsm.FSM.InitialState):
        pass

    class FinalState(SimpleState, fsm.FSM.FinalState):
        pass 
    
    def __init__(self, states = []):
        SimpleState.__init__(self)
        fsm.FSM.__init__(self, states, initial = CompositeState.InitialState(),
                         final = CompositeState.FinalState())
    
    def start(self):
        return fsm.FSM.start(self)
    
    def stop(self):
        return fsm.FSM.stop(self)
    
    def __contains__(self, other):
        return fsm.FSM.__contains__(self, other)


class HSM(object):
    
    class TopState(CompositeState):
        pass
    
    def __init__(self, states = []):
        object.__init__(self)
        self.top = HSM.TopState()
    
    def start(self):
        self.current = self.top.initial
        return self.dispatch(SimpleState.EnterEvent)
    
    def stop(self):
        self.top.final.add_final_transition_to_other(other=self.current)
        return self.dispatch(SimpleState.ExitEvent)
    
    def add_start_activity(self, activity):
        self.top.add_start_activity(activity)
    
    def add_stop_activity(self, activity):
        self.top.add_stop_activity(activity)
    
    def add_on_transition_completed_activity(self, activity):
        self.top.add_on_transition_completed_activity(activity)
    
    def dispatch(self, event):
        while True:
            response = self._dipatch_to_current(event)
            
            if event == SimpleState.EnterEvent:
                event = SimpleState.UnnamedEvent
            elif not response.was_transition_requested():
                break
        return response

    def _dipatch_to_current(self, event):
        
        response = self.current.process_event(event)
        
        if not response.was_transition_requested():
            return response

        source_stack = self.current.get_parent_stack()
        source_set = set(source_stack)
        target_stack = response.transition.target.get_parent_stack()
        target_set = set(target_stack)
        common_set = target_set & source_set
        exit_set = source_set - common_set
        enter_set = target_set - common_set
        exit_stack = [st for st in source_stack if st in exit_set ]
        exit_stack.reverse()
        enter_stack = [st for st in target_stack if st in enter_set ]

        for st in exit_stack:
            exit_response = st.exit()
                
            if exit_response.did_act():
                activity = True
        
        for st in enter_stack:
            enter_response = st.enter()

            if enter_response.did_act():
                activity = True
        
        self.current = enter_stack[-1]
        self.top.state_change_activities.process_event(Event)
        
        start_response = self.current.start()
        return TransitionAndActivityResult(response.activity, response.transition)

    def fsm_dipatch_to_current(self, event):
        '''_dipatch_to_state(state, event) -> active_state, did_transition'''

        if self.current == self.initial and fsm.State.EnterEvent == fsm.get_object_class(event) \
           and self.no_initial_transition:
            return False, False, None
            
        if fsm.State.ExitEvent == fsm.get_object_class(event) and self.no_final_transition:
            return False, False, None

        activity, transition, target = self.current.process_event(event)
        
        if transition and None != target:
            self.current.exit()
            self.current = target
            self.current.enter()
            self.state_change_activities.process_event(Event)
        
        return activity, transition, target
