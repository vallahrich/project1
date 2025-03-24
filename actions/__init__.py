"""
Custom actions for the email assistant Rasa Pro chatbot.
"""

# Import all actions for action_endpoint to discover
from actions.email_check_actions import ActionCheckNewMail, ActionReadMail
from actions.email_reply_actions import ActionDraftReply, ActionSendReply
from actions.email_organize_actions import ActionSortMail, ActionLabelMail

# For Rasa to discover the actions
all_actions = [
    ActionCheckNewMail(),
    ActionReadMail(),
    ActionDraftReply(),
    ActionSendReply(),
    ActionSortMail(),
    ActionLabelMail()
]