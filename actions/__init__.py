"""
Custom actions for the enhanced email assistant Rasa Pro chatbot.
"""

# Import original actions
from actions.email_check_actions import ActionCheckNewMail, ActionReadMail
from actions.email_reply_actions import ActionDraftReply, ActionSendReply
from actions.email_organize_actions import ActionSortMail, ActionLabelMail

# Import validation actions
from actions.validate_reply_type import ValidateReplyType, ValidateReviewOption

# Import new enhanced actions
from actions.improved_email_actions import ActionListEmails, ActionReadSelectedEmail, ActionNavigateEmails, ValidateSelectedEmail
from actions.improved_email_organize_actions import ActionGetLabelSuggestions, ActionApplySelectedLabel
from actions.improved_email_reply_actions import ActionInitiateReply, ActionGenerateReplyDraft

# For Rasa to discover the actions
all_actions = [
    # Original actions
    ActionCheckNewMail(),
    ActionReadMail(),
    ActionDraftReply(),
    ActionSendReply(),
    ActionSortMail(),
    ActionLabelMail(),
    
    # Validation actions
    ValidateReplyType(),
    ValidateSelectedEmail(),
    ValidateReviewOption(),
    
    # New enhanced actions
    ActionListEmails(),
    ActionReadSelectedEmail(),
    ActionNavigateEmails(),
    ActionGetLabelSuggestions(),
    ActionApplySelectedLabel(),
    ActionInitiateReply(),
    ActionGenerateReplyDraft(),
]