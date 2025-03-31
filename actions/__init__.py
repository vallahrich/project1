"""
Custom actions for the enhanced email assistant.
"""
# Import basic actions
from actions.basic_email_actions import ActionDeleteEmail, ActionMarkAsRead

# Import improved email actions
from actions.improved_email_actions import ActionListEmails, ActionReadSelectedEmail, ValidateSelectedEmail, ActionNavigateEmails

# Import email reply actions
from actions.improved_email_reply_actions import ActionInitiateReply, ActionGenerateReplyDraft, ActionSendReply, ActionEditReplyDraft

# Import email organization actions
from actions.improved_email_organize_actions import ActionGetLabelSuggestions, ActionApplySelectedLabel

# Import special handling actions
from actions.special_email_handling import ActionCheckForNoReply

# Import validation actions
from actions.validate_email_response import ValidateEmailResponse
from actions.validate_review_option import ValidateReviewOption

# Import new input prompt actions
from actions.email_reply_prompts import ActionSelectInputPrompt, ActionSetUserInput

# Import reset email slots action
from actions.reset_email_slots import ActionResetEmailSlots

# Import calendar actions
from actions.add_calendar import ActionAddCalendarEvent

# Import emergency Twilio action
from actions.emergency_twillio import ActionEmergencyTwilio


# For Rasa to discover the actions
all_actions = [
    # Email actions
    ActionListEmails(),
    ActionReadSelectedEmail(), 
    ActionNavigateEmails(), 
    ValidateSelectedEmail(),
    
    # Email operations
    ActionDeleteEmail(),
    ActionMarkAsRead(),
    
    # Reply actions
    ActionInitiateReply(),
    ActionGenerateReplyDraft(),
    ActionEditReplyDraft(),  
    ActionSendReply(),
    ActionSelectInputPrompt(),
    ActionSetUserInput(), 
    
    # Organization actions
    ActionGetLabelSuggestions(),
    ActionApplySelectedLabel(),
    
    # Special handling actions
    ActionCheckForNoReply(),

    # Validation actions
    ValidateEmailResponse(),
    ValidateReviewOption(), 
    ActionResetEmailSlots(),
    
    # Calendar actions
    ActionAddCalendarEvent(),
    
    # Emergency actions
    ActionEmergencyTwilio(),
]