import collections.abc
import json
import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDuplicates
from hydrus.client import ClientTime
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtInit
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUIMPV
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaFileFilter

class EditChooseMultiple( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, choice_tuples: list ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._checkboxes = ClientGUICommon.BetterCheckBoxList( self )
        
        self._checkboxes.setMinimumSize( QC.QSize( 320, 420 ) )
        
        try:
            
            choice_tuples.sort()
            
        except TypeError:
            
            try:
                
                choice_tuples.sort( key = lambda t: t[0] )
                
            except TypeError:
                
                pass # fugg
                
            
        
        for ( index, ( label, data, selected ) ) in enumerate( choice_tuples ):
            
            self._checkboxes.Append( label, data )
            
            if selected:
                
                self._checkboxes.Check( index )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._checkboxes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ) -> list:
        
        return self._checkboxes.GetValue()
        
    
class EditDefaultImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__(
        self,
        parent: QW.QWidget,
        url_classes,
        parsers,
        url_class_keys_to_parser_keys,
        file_post_default_tag_import_options,
        watchable_default_tag_import_options,
        url_class_keys_to_tag_import_options,
        file_post_default_note_import_options,
        watchable_default_note_import_options,
        url_class_keys_to_note_import_options
    ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._url_classes = url_classes
        self._parsers = parsers
        self._url_class_keys_to_parser_keys = url_class_keys_to_parser_keys
        self._parser_keys_to_parsers = { parser.GetParserKey() : parser for parser in self._parsers }
        
        self._url_class_keys_to_tag_import_options = dict( url_class_keys_to_tag_import_options )
        self._url_class_keys_to_note_import_options = dict( url_class_keys_to_note_import_options )
        
        #
        
        show_downloader_options = True
        allow_default_selection = False
        
        self._file_post_default_import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._file_post_default_import_options_button.SetTagImportOptions( file_post_default_tag_import_options )
        self._file_post_default_import_options_button.SetNoteImportOptions( file_post_default_note_import_options )
        
        self._watchable_default_import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._watchable_default_import_options_button.SetTagImportOptions( watchable_default_tag_import_options )
        self._watchable_default_import_options_button.SetNoteImportOptions( watchable_default_note_import_options )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, CGLC.COLUMN_LIST_DEFAULT_TAG_IMPORT_OPTIONS.ID, 15, self._ConvertDataToListCtrlTuples, activation_callback = self._Edit )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl_panel.AddButton( 'copy tags', self._CopyTags, enabled_check_func = self._OnlyOneTIOSelected )
        self._list_ctrl_panel.AddButton( 'copy notes', self._CopyNotes, enabled_check_func = self._OnlyOneNIOSelected )
        self._list_ctrl_panel.AddButton( 'paste', self._Paste, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddButton( 'clear tags', self._ClearTags, enabled_check_func = self._AtLeastOneTIOSelected )
        self._list_ctrl_panel.AddButton( 'clear notes', self._ClearNotes, enabled_check_func = self._AtLeastOneNIOSelected )
        
        #
        
        eligible_url_classes = [ url_class for url_class in url_classes if url_class.GetURLType() in ( HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE ) and url_class.GetClassKey() in self._url_class_keys_to_parser_keys ]
        
        self._list_ctrl.AddDatas( eligible_url_classes )
        
        self._list_ctrl.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'default for file posts: ', self._file_post_default_import_options_button ) )
        rows.append( ( 'default for watchable urls: ', self._watchable_default_import_options_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AtLeastOneNIOSelected( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        for url_class in selected:
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_note_import_options:
                
                return True
                
            
        
        return False
        
    
    def _AtLeastOneTIOSelected( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        for url_class in selected:
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_tag_import_options:
                
                return True
                
            
        
        return False
        
    
    def _ConvertDataToListCtrlTuples( self, url_class ):
        
        url_class_key = url_class.GetClassKey()
        
        name = url_class.GetName()
        url_type = url_class.GetURLType()
        
        pretty_name = name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        defaults_components = []
        
        if url_class_key in self._url_class_keys_to_tag_import_options:
            
            defaults_components.append( 'tags' )
            
        
        if url_class_key in self._url_class_keys_to_note_import_options:
            
            defaults_components.append( 'notes' )
            
        
        pretty_defaults_set = ', '.join( defaults_components )
        
        display_tuple = ( pretty_name, pretty_url_type, pretty_defaults_set )
        sort_tuple = ( name, pretty_url_type, pretty_defaults_set )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ClearNotes( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear set note import options for all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            url_classes_to_clear = self._list_ctrl.GetData( only_selected = True )
            
            for url_class in url_classes_to_clear:
                
                url_class_key = url_class.GetClassKey()
                
                if url_class_key in self._url_class_keys_to_note_import_options:
                    
                    del self._url_class_keys_to_note_import_options[ url_class_key ]
                    
                
            
            self._list_ctrl.UpdateDatas( url_classes_to_clear )
            
        
    
    def _ClearTags( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear set tag import options for all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            url_classes_to_clear = self._list_ctrl.GetData( only_selected = True )
            
            for url_class in url_classes_to_clear:
                
                url_class_key = url_class.GetClassKey()
                
                if url_class_key in self._url_class_keys_to_tag_import_options:
                    
                    del self._url_class_keys_to_tag_import_options[ url_class_key ]
                    
                
            
            self._list_ctrl.UpdateDatas( url_classes_to_clear )
            
        
    
    def _CopyNotes( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_note_import_options:
                
                note_import_options = self._url_class_keys_to_note_import_options[ url_class_key ]
                
                json_string = note_import_options.DumpToString()
                
                HG.client_controller.pub( 'clipboard', 'text', json_string )
                
            
        
    
    def _CopyTags( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_tag_import_options:
                
                tag_import_options = self._url_class_keys_to_tag_import_options[ url_class_key ]
                
                json_string = tag_import_options.DumpToString()
                
                HG.client_controller.pub( 'clipboard', 'text', json_string )
                
            
        
    
    def _Edit( self ):
        
        url_classes_to_edit = self._list_ctrl.GetData( only_selected = True )
        
        for url_class in url_classes_to_edit:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag import options' ) as dlg:
                
                tag_import_options = self._GetDefaultTagImportOptions( url_class )
                note_import_options = self._GetDefaultNoteImportOptions( url_class )
                
                show_downloader_options = True
                allow_default_selection = True
                
                panel = ClientGUIImportOptions.EditImportOptionsPanel( dlg, show_downloader_options, allow_default_selection )
                
                panel.SetTagImportOptions( tag_import_options )
                panel.SetNoteImportOptions( note_import_options )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    url_class_key = url_class.GetClassKey()
                    
                    if url_class_key in self._url_class_keys_to_tag_import_options:
                        
                        del self._url_class_keys_to_tag_import_options[ url_class_key ]
                        
                    
                    tag_import_options = panel.GetTagImportOptions()
                    
                    if not tag_import_options.IsDefault():
                        
                        self._url_class_keys_to_tag_import_options[ url_class_key ] = tag_import_options
                        
                    
                    if url_class_key in self._url_class_keys_to_note_import_options:
                        
                        del self._url_class_keys_to_note_import_options[ url_class_key ]
                        
                    
                    note_import_options = panel.GetNoteImportOptions()
                    
                    if not note_import_options.IsDefault():
                        
                        self._url_class_keys_to_note_import_options[ url_class_key ] = note_import_options
                        
                    
                else:
                    
                    break
                    
                
            
        
        self._list_ctrl.UpdateDatas( url_classes_to_edit )
        
    
    def _GetDefaultNoteImportOptions( self, url_class ):
        
        url_class_key = url_class.GetClassKey()
        
        if url_class_key in self._url_class_keys_to_note_import_options:
            
            note_import_options = self._url_class_keys_to_note_import_options[ url_class_key ]
            
        else:
            
            url_type = url_class.GetURLType()
            
            if url_type == HC.URL_TYPE_POST:
                
                note_import_options = self._file_post_default_import_options_button.GetNoteImportOptions()
                
            elif url_type == HC.URL_TYPE_WATCHABLE:
                
                note_import_options = self._watchable_default_import_options_button.GetNoteImportOptions()
                
            else:
                
                raise HydrusExceptions.URLClassException( 'Could not find note import options for that kind of URL Class!' )
                
            
            note_import_options = note_import_options.Duplicate()
            
            note_import_options.SetIsDefault( True )
            
        
        return note_import_options
        
    
    def _GetDefaultTagImportOptions( self, url_class ):
        
        url_class_key = url_class.GetClassKey()
        
        if url_class_key in self._url_class_keys_to_tag_import_options:
            
            tag_import_options = self._url_class_keys_to_tag_import_options[ url_class_key ]
            
        else:
            
            url_type = url_class.GetURLType()
            
            if url_type == HC.URL_TYPE_POST:
                
                tag_import_options = self._file_post_default_import_options_button.GetTagImportOptions()
                
            elif url_type == HC.URL_TYPE_WATCHABLE:
                
                tag_import_options = self._watchable_default_import_options_button.GetTagImportOptions()
                
            else:
                
                raise HydrusExceptions.URLClassException( 'Could not find tag import options for that kind of URL Class!' )
                
            
            tag_import_options = tag_import_options.Duplicate()
            
            tag_import_options.SetIsDefault( True )
            
        
        return tag_import_options
        
    
    def _OnlyOneNIOSelected( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_note_import_options:
                
                return True
                
            
        
        return False
        
    
    def _OnlyOneTIOSelected( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_tag_import_options:
                
                return True
                
            
        
        return False
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            unknown_import_options = HydrusSerialisable.CreateFromString( raw_text )
            
            if isinstance( unknown_import_options, TagImportOptions.TagImportOptions ):
                
                insert_dict = self._url_class_keys_to_tag_import_options
                
            elif isinstance( unknown_import_options, NoteImportOptions.NoteImportOptions ):
                
                insert_dict = self._url_class_keys_to_note_import_options
                
            else:
                
                raise Exception( 'Not a Tag or Note Import Options!' )
                
            
            for url_class in self._list_ctrl.GetData( only_selected = True ):
                
                url_class_key = url_class.GetClassKey()
                
                insert_dict[ url_class_key ] = unknown_import_options.Duplicate()
                
            
            self._list_ctrl.UpdateDatas()
            
        except Exception as e:
            
            ClientGUIFunctions.PresentClipboardParseError( self, raw_text, 'An instance of JSON-serialised tag or note import options', e )
            
        
    
    def GetValue( self ):
        
        file_post_default_tag_import_options = self._file_post_default_import_options_button.GetTagImportOptions()
        watchable_default_tag_import_options = self._watchable_default_import_options_button.GetTagImportOptions()
        
        file_post_default_note_import_options = self._file_post_default_import_options_button.GetNoteImportOptions()
        watchable_default_note_import_options = self._watchable_default_import_options_button.GetNoteImportOptions()
        
        return (
            file_post_default_tag_import_options,
            watchable_default_tag_import_options,
            self._url_class_keys_to_tag_import_options,
            file_post_default_note_import_options,
            watchable_default_note_import_options,
            self._url_class_keys_to_note_import_options
        )
        
    
class EditDeleteFilesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    SPECIAL_CHOICE_CUSTOM = 0
    SPECIAL_CHOICE_NO_REASON = 1
    
    def __init__( self, parent: QW.QWidget, media, default_reason, suggested_file_service_key = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._default_reason = default_reason
        
        local_file_services = list( HG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) ) )
        
        if suggested_file_service_key is None:
            
            suggested_file_service_key = local_file_services[0].GetServiceKey()
            
        
        self._media = self._FilterForDeleteLock( ClientMedia.FlattenMedia( media ), suggested_file_service_key )
        
        self._question_is_already_resolved = len( self._media ) == 0
        
        ( self._all_files_have_existing_file_deletion_reasons, self._existing_shared_file_deletion_reason ) = self._GetExistingSharedFileDeletionReason()
        
        self._simple_description = ClientGUICommon.BetterStaticText( self, label = 'init' )
        
        self._num_actionable_local_file_services = 0
        self._permitted_action_choices = []
        self._this_dialog_includes_service_keys = False
        
        self._InitialisePermittedActionChoices()
        
        self._action_radio = ClientGUICommon.BetterRadioBox( self, choices = self._permitted_action_choices, vertical = True )
        
        self._action_radio.Select( 0 )
        
        selection_success = False
        
        if HG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_special_action' ):
            
            last_advanced_file_deletion_special_action = HG.client_controller.new_options.GetNoneableString( 'last_advanced_file_deletion_special_action' )
            
            selection_success = self._TryToSelectAction( last_advanced_file_deletion_special_action )
            
        
        if not selection_success:
            
            self._TryToSelectAction( suggested_file_service_key )
            
        
        self._reason_panel = ClientGUICommon.StaticBox( self, 'reason' )
        
        existing_reason_was_in_list = False
        
        permitted_reason_choices = []
        
        if self._existing_shared_file_deletion_reason is not None and default_reason == self._existing_shared_file_deletion_reason:
            
            existing_reason_was_in_list = True
            
            permitted_reason_choices.append( ( 'keep existing reason: {}'.format( default_reason ), default_reason ) )
            
        else:
            
            permitted_reason_choices.append( ( default_reason, default_reason ) )
            
        
        if HG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_reason' ):
            
            last_advanced_file_deletion_reason = HG.client_controller.new_options.GetNoneableString( 'last_advanced_file_deletion_reason' )
            
        else:
            
            last_advanced_file_deletion_reason = None
            
        
        if last_advanced_file_deletion_reason is None:
            
            selection_index = 0 # default, top row
            
        else:
            
            selection_index = None # text or custom
            
        
        for ( i, s ) in enumerate( HG.client_controller.new_options.GetStringList( 'advanced_file_deletion_reasons' ) ):
            
            if self._existing_shared_file_deletion_reason is not None and s == self._existing_shared_file_deletion_reason and not existing_reason_was_in_list:
                
                existing_reason_was_in_list = True
                
                permitted_reason_choices.append( ( 'keep existing reason: {}'.format( s ), s ) )
                
            else:
                
                permitted_reason_choices.append( ( s, s ) )
                
            
            if last_advanced_file_deletion_reason is not None and s == last_advanced_file_deletion_reason:
                
                selection_index = i + 1
                
            
        
        if self._existing_shared_file_deletion_reason is not None and not existing_reason_was_in_list:
            
            permitted_reason_choices.append( ( 'keep existing reason: {}'.format( self._existing_shared_file_deletion_reason ), self._existing_shared_file_deletion_reason ) )
            
            selection_index = len( permitted_reason_choices ) - 1
            
        
        custom_index = len( permitted_reason_choices )
        
        permitted_reason_choices.append( ( 'custom', self.SPECIAL_CHOICE_CUSTOM ) )
        
        if self._all_files_have_existing_file_deletion_reasons and self._existing_shared_file_deletion_reason is None:
            
            permitted_reason_choices.append( ( '(all files have existing file deletion reasons and they differ): do not alter them.', self.SPECIAL_CHOICE_NO_REASON ) )
            
            selection_index = len( permitted_reason_choices ) - 1
            
        
        self._reason_radio = ClientGUICommon.BetterRadioBox( self._reason_panel, choices = permitted_reason_choices, vertical = True )
        
        self._custom_reason = QW.QLineEdit( self._reason_panel )
        
        if selection_index is None:
            
            selection_index = custom_index
            
            self._custom_reason.setText( last_advanced_file_deletion_reason )
            
        
        self._reason_radio.Select( selection_index )
        
        #
        
        ( file_service_key, list_of_service_keys_to_content_updates, save_reason, involves_physical_delete, description ) = self._action_radio.GetValue()
        
        self._simple_description.setText( description )
        
        if len( self._permitted_action_choices ) == 1:
            
            self._action_radio.hide()
            self._action_radio.setEnabled( False )
            
        else:
            
            self._simple_description.hide()
            
        
        if not HG.client_controller.new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ):
            
            self._reason_panel.hide()
            self._reason_panel.setEnabled( False )
            
        
        self._action_radio.radioBoxChanged.connect( self._UpdateControls )
        self._reason_radio.radioBoxChanged.connect( self._UpdateControls )
        
        self._UpdateControls()
        
        #
        
        self._reason_panel.Add( self._reason_radio, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'custom reason: ', self._custom_reason ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._reason_panel, rows )
        
        self._reason_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_description, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._action_radio, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._reason_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        QP.CallAfter( self._SetFocus )
        
    
    def _FilterForDeleteLock( self, media, suggested_file_service_key: bytes ):
        
        service = HG.client_controller.services_manager.GetService( suggested_file_service_key )
        
        if service.GetServiceType() in HC.LOCAL_FILE_SERVICES:
            
            media = ClientMediaFileFilter.FilterAndReportDeleteLockFailures( media )
            
        
        return media
        
    
    def _GetExistingSharedFileDeletionReason( self ):
        
        all_files_have_existing_file_deletion_reasons = True
        reasons = set()
        
        for m in self._media:
            
            lm = m.GetLocationsManager()
            
            if not lm.HasLocalFileDeletionReason():
                
                all_files_have_existing_file_deletion_reasons = False
                
                return ( all_files_have_existing_file_deletion_reasons, None )
                
            
            reason = lm.GetLocalFileDeletionReason()
            
            reasons.add( reason )
            
        
        shared_reason = None
        
        if all_files_have_existing_file_deletion_reasons and len( reasons ) == 1:
            
            shared_reason = list( reasons )[0]
            
        
        return ( all_files_have_existing_file_deletion_reasons, shared_reason )
        
    
    def _GetReason( self ):
        
        if self._reason_panel.isEnabled():
            
            reason = self._reason_radio.GetValue()
            
            if reason == self.SPECIAL_CHOICE_CUSTOM:
                
                reason = self._custom_reason.text()
                
            elif reason == self.SPECIAL_CHOICE_NO_REASON:
                
                reason = None
                
            
        else:
            
            if self._all_files_have_existing_file_deletion_reasons or self._existing_shared_file_deletion_reason is not None:
                
                # do not overwrite
                reason = None
                
            else:
                
                reason = self._default_reason
                
            
        
        return reason
        
    
    def _InitialisePermittedActionChoices( self ):
        
        possible_file_service_keys = []
        
        local_file_services = list( HG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) ) )
        local_file_service_keys = { service.GetServiceKey() for service in local_file_services }
        
        possible_file_service_keys.extend( ( ( lfs.GetServiceKey(), lfs.GetServiceKey() ) for lfs in local_file_services ) )
        
        possible_file_service_keys.append( ( CC.TRASH_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
        
        if HG.client_controller.new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ):
            
            possible_file_service_keys.append( ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
            
        
        possible_file_service_keys.extend( ( ( rfs.GetServiceKey(), rfs.GetServiceKey() ) for rfs in HG.client_controller.services_manager.GetServices( ( HC.FILE_REPOSITORY, ) ) ) )
        
        keys_to_hashes = { ( selection_file_service_key, deletee_file_service_key ) : [ m.GetHash() for m in self._media if selection_file_service_key in m.GetLocationsManager().GetCurrent() ] for ( selection_file_service_key, deletee_file_service_key ) in possible_file_service_keys }
        
        trashed_key = ( CC.TRASH_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
        combined_key = ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
        
        if trashed_key in keys_to_hashes and combined_key in keys_to_hashes and keys_to_hashes[ trashed_key ] == keys_to_hashes[ combined_key ]:
            
            del keys_to_hashes[ combined_key ]
            
        
        possible_file_service_keys_and_hashes = [ ( fsk, keys_to_hashes[ fsk ] ) for fsk in possible_file_service_keys if fsk in keys_to_hashes and len( keys_to_hashes[ fsk ] ) > 0 ]
        
        self._num_actionable_local_file_services = len( local_file_service_keys.intersection( ( fsk[0] for ( fsk, hashes ) in possible_file_service_keys_and_hashes ) ) )
        
        all_local_jobs = []
        num_local_services_done = 0
        
        for ( fsk, hashes ) in possible_file_service_keys_and_hashes:
            
            num_to_delete = len( hashes )
            
            ( selection_file_service_key, deletee_file_service_key ) = fsk
            
            deletee_service = HG.client_controller.services_manager.GetService( deletee_file_service_key )
            
            deletee_service_type = deletee_service.GetServiceType()
            
            if deletee_service_type == HC.LOCAL_FILE_DOMAIN:
                
                self._this_dialog_includes_service_keys = True
                
                if num_to_delete == 1:
                    
                    file_desc = 'one file'
                    
                else:
                    
                    file_desc = '{} files'.format( HydrusData.ToHumanInt( num_to_delete ) )
                    
                
                if self._num_actionable_local_file_services == 1:
                    
                    template = 'Send {} from {} to trash?'
                    
                else:
                    
                    template = 'Remove {} from {}?'
                    
                
                text = template.format( file_desc, deletee_service.GetName() )
                
                chunks_of_hashes = HydrusLists.SplitListIntoChunks( hashes, 64 )
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
                
                list_of_service_keys_to_content_updates = [ { deletee_file_service_key : [ content_update ] } for content_update in content_updates ]
                
                all_local_jobs.extend( list_of_service_keys_to_content_updates )
                
                save_reason = True
                
                involves_physical_delete = False
                
                num_local_services_done += 1
                
                # this is an ugly place to put this, and the mickey-mouse append, but it works
                if self._num_actionable_local_file_services > 1 and num_local_services_done == self._num_actionable_local_file_services:
                    
                    self._permitted_action_choices.append( ( text, ( deletee_file_service_key, list_of_service_keys_to_content_updates, save_reason, involves_physical_delete, text ) ) )
                    
                    deletee_file_service_key = CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY
                    
                    h = [ m.GetHash() for m in self._media if CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY in m.GetLocationsManager().GetCurrent() ]
                    
                    chunks_of_hashes = HydrusLists.SplitListIntoChunks( h, 64 )
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
                    
                    list_of_service_keys_to_content_updates = [ { deletee_file_service_key : [ content_update ] } for content_update in content_updates ]
                    
                    text = 'Delete from all local services? (force send to trash)'
                    
                    save_reason = True
                    
                    involves_physical_delete = False
                    
                
            elif deletee_service_type == HC.FILE_REPOSITORY:
                
                if deletee_service.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_PETITION ):
                    
                    self._this_dialog_includes_service_keys = True
                    
                    if num_to_delete == 1:
                        
                        file_desc = 'one file'
                        
                    else:
                        
                        file_desc = '{} files'.format( HydrusData.ToHumanInt( num_to_delete ) )
                        
                    
                    if deletee_service.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_MODERATE ):
                        
                        text = 'Admin-delete {} from {}?'.format( file_desc, deletee_service.GetName() )
                        
                        save_reason = False
                        reason = 'admin'
                        
                    else:
                        
                        text = 'Petition {} from {}?'.format( file_desc, deletee_service.GetName() )
                        
                        save_reason = True
                        reason = None
                        
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes, reason = reason ) ]
                    
                    list_of_service_keys_to_content_updates = [ { deletee_file_service_key : content_updates } ]
                    
                    involves_physical_delete = False
                    
                
            elif deletee_file_service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
                
                # do a physical delete now, skipping or force-removing from trash
                
                deletee_file_service_key = 'physical_delete'
                
                if selection_file_service_key == CC.TRASH_SERVICE_KEY:
                    
                    suffix = 'trashed '
                    
                else:
                    
                    suffix = ''
                    
                
                if num_to_delete == 1:
                    
                    suffix = 'one {}file'.format( suffix )
                    
                else:
                    
                    suffix = '{} {}files'.format( HydrusData.ToHumanInt( num_to_delete ), suffix )
                    
                
                text = 'Permanently delete {}?'.format( suffix )
                
                chunks_of_hashes = HydrusLists.SplitListIntoChunks( hashes, 64 )
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
                
                list_of_service_keys_to_content_updates = [ { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] } for content_update in content_updates ]
                
                save_reason = True
                
                involves_physical_delete = True
                
            
            self._permitted_action_choices.append( ( text, ( deletee_file_service_key, list_of_service_keys_to_content_updates, save_reason, involves_physical_delete, text ) ) )
            
        
        if self._num_actionable_local_file_services == 1 and not HC.options[ 'confirm_trash' ]:
            
            # this dialog will never show
            self._question_is_already_resolved = True
            
        
        if HG.client_controller.new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ):
            
            hashes = [ m.GetHash() for m in self._media if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in m.GetLocationsManager().GetCurrent() ]
            
            num_to_delete = len( hashes )
            
            if num_to_delete > 0:
                
                if num_to_delete == 1:
                    
                    text = 'Permanently delete this file and do not save a deletion record?'
                    
                else:
                    
                    text = 'Permanently delete these ' + HydrusData.ToHumanInt( num_to_delete ) + ' files and do not save a deletion record?'
                    
                
                chunks_of_hashes = list( HydrusLists.SplitListIntoChunks( hashes, 64 ) ) # iterator, so list it to use it more than once, jej
                
                list_of_service_keys_to_content_updates = []
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
                
                list_of_service_keys_to_content_updates.extend( [ { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] } for content_update in content_updates ] )
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
                
                list_of_service_keys_to_content_updates.extend( [ { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] } for content_update in content_updates ] )
                
                save_reason = False
                
                involves_physical_delete = True
                
                self._permitted_action_choices.append( ( text, ( 'clear_delete', list_of_service_keys_to_content_updates, save_reason, involves_physical_delete, text ) ) )
                
            
        
        if len( self._permitted_action_choices ) == 0:
            
            raise HydrusExceptions.CancelledException( 'No valid delete choices!' )
            
        
    
    def _SetFocus( self ):
        
        if self._action_radio.isEnabled():
            
            self._action_radio.setFocus( QC.Qt.OtherFocusReason )
            
        elif self._reason_panel.isEnabled():
            
            self._reason_radio.setFocus( QC.Qt.OtherFocusReason )
            
        
    
    def _TryToSelectAction( self, action ) -> bool:
        
        if action is None:
            
            return False
            
        
        # this is a mess since action could be 'clear_delete' or a file service key
        
        if isinstance( action, bytes ):
            
            action = action.hex()
            
        
        for ( i, choice ) in enumerate( self._permitted_action_choices ):
            
            deletee_file_service_key = choice[1][0]
            
            if isinstance( deletee_file_service_key, bytes ):
                
                comparison_text = deletee_file_service_key.hex()
                
            else:
                
                comparison_text = deletee_file_service_key
                
            
            if comparison_text == action:
                
                self._action_radio.Select( i )
                
                return True
                
            
        
        return False
        
    
    def _UpdateControls( self ):
        
        ( file_service_key, list_of_service_keys_to_content_updates, save_reason, involves_physical_delete, description ) = self._action_radio.GetValue()
        
        reason_permitted = save_reason
        
        if reason_permitted:
            
            self._reason_panel.setEnabled( True )
            
            reason = self._reason_radio.GetValue()
            
            if reason == self.SPECIAL_CHOICE_CUSTOM:
                
                self._custom_reason.setEnabled( True )
                
            else:
                
                self._custom_reason.setEnabled( False )
                
            
        else:
            
            self._reason_panel.setEnabled( False )
            
        
    
    def GetValue( self ):
        
        if len( self._permitted_action_choices ) == 0 or len( self._media ) == 0:
            
            return ( False, [] )
            
        
        involves_physical_delete = False
        
        ( file_service_key, list_of_service_keys_to_content_updates, save_reason, involves_physical_delete, description ) = self._action_radio.GetValue()
        
        if save_reason:
            
            reason = self._GetReason()
            
            for service_keys_to_content_updates in list_of_service_keys_to_content_updates:
                
                for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                    
                    for content_update in content_updates:
                        
                        content_update.SetReason( reason )
                        
                    
                
            
        
        save_action = True
        
        if isinstance( file_service_key, bytes ):
            
            last_advanced_file_deletion_special_action = file_service_key.hex()
            
        else:
            
            previous_last_advanced_file_deletion_special_action = HG.client_controller.new_options.GetNoneableString( 'last_advanced_file_deletion_special_action' )
            
            # if there is nothing to do but physically delete, then we don't want to overwrite an existing 'use service' setting
            # HACKMODE ALERT. len() == 64 is a stupid test for 'looks like a service key mate'
            if ( previous_last_advanced_file_deletion_special_action is None or len( previous_last_advanced_file_deletion_special_action ) == 64 ) and not self._this_dialog_includes_service_keys:
                
                save_action = False
                
            
            last_advanced_file_deletion_special_action = file_service_key
            
        
        if save_action and HG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_special_action' ):
            
            HG.client_controller.new_options.SetNoneableString( 'last_advanced_file_deletion_special_action', last_advanced_file_deletion_special_action )
            
        
        if save_reason and HG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_reason' ):
            
            reasons_ok = self._reason_radio.isVisible() and self._reason_radio.isEnabled()
            
            user_selected_existing_or_make_no_change = reason == self._existing_shared_file_deletion_reason or reason is None
            
            if reasons_ok and not user_selected_existing_or_make_no_change:
                
                if self._reason_radio.GetCurrentIndex() <= 0:
                    
                    last_advanced_file_deletion_reason = None
                    
                else:
                    
                    last_advanced_file_deletion_reason = reason
                    
                
                HG.client_controller.new_options.SetNoneableString( 'last_advanced_file_deletion_reason', last_advanced_file_deletion_reason )
                
            
        
        return ( involves_physical_delete, list_of_service_keys_to_content_updates )
        
    
    def QuestionIsAlreadyResolved( self ):
        
        return self._question_is_already_resolved
        
    
class EditDuplicateContentMergeOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, duplicate_action, duplicate_content_merge_options: ClientDuplicates.DuplicateContentMergeOptions, for_custom_action = False ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._duplicate_action = duplicate_action
        
        #
        
        tag_services_panel = ClientGUICommon.StaticBox( self, 'tag services' )
        
        tag_services_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( tag_services_panel )
        
        self._tag_service_actions = ClientGUIListCtrl.BetterListCtrl( tag_services_listctrl_panel, CGLC.COLUMN_LIST_DUPLICATE_CONTENT_MERGE_OPTIONS_TAG_SERVICES.ID, 5, self._ConvertTagDataToListCtrlTuple, delete_key_callback = self._DeleteTag, activation_callback = self._EditTag )
        
        tag_services_listctrl_panel.SetListCtrl( self._tag_service_actions )
        
        tag_services_listctrl_panel.AddButton( 'add', self._AddTag )
        tag_services_listctrl_panel.AddButton( 'edit', self._EditTag, enabled_only_on_selection = True )
        tag_services_listctrl_panel.AddButton( 'delete', self._DeleteTag, enabled_only_on_selection = True )
        
        #
        
        rating_services_panel = ClientGUICommon.StaticBox( self, 'rating services' )
        
        rating_services_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( rating_services_panel )
        
        self._rating_service_actions = ClientGUIListCtrl.BetterListCtrl( rating_services_listctrl_panel, CGLC.COLUMN_LIST_DUPLICATE_CONTENT_MERGE_OPTIONS_RATING_SERVICES.ID, 5, self._ConvertRatingDataToListCtrlTuple, delete_key_callback = self._DeleteRating, activation_callback = self._EditRating )
        
        rating_services_listctrl_panel.SetListCtrl( self._rating_service_actions )
        
        rating_services_listctrl_panel.AddButton( 'add', self._AddRating )
        if self._duplicate_action == HC.DUPLICATE_BETTER: # because there is only one valid action otherwise
            
            rating_services_listctrl_panel.AddButton( 'edit', self._EditRating, enabled_only_on_selection = True )
            
        rating_services_listctrl_panel.AddButton( 'delete', self._DeleteRating, enabled_only_on_selection = True )
        
        #
        
        self._sync_archive_action = ClientGUICommon.BetterChoice( self )
        
        self._sync_archive_action.addItem( 'make no change', ClientDuplicates.SYNC_ARCHIVE_NONE )
        self._sync_archive_action.addItem( 'if one is archived, archive the other', ClientDuplicates.SYNC_ARCHIVE_IF_ONE_DO_BOTH )
        self._sync_archive_action.addItem( 'always archive both', ClientDuplicates.SYNC_ARCHIVE_DO_BOTH_REGARDLESS )
        
        self._sync_urls_action = ClientGUICommon.BetterChoice( self )
        self._sync_file_modified_date_action = ClientGUICommon.BetterChoice( self )
        self._sync_notes_action = ClientGUICommon.BetterChoice( self )
        
        self._sync_urls_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_NONE ], HC.CONTENT_MERGE_ACTION_NONE )
        self._sync_file_modified_date_action.addItem( HC.content_modified_date_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_NONE ], HC.CONTENT_MERGE_ACTION_NONE )
        self._sync_notes_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_NONE ], HC.CONTENT_MERGE_ACTION_NONE )
        
        if self._duplicate_action == HC.DUPLICATE_BETTER:
            
            self._sync_urls_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_COPY ], HC.CONTENT_MERGE_ACTION_COPY )
            self._sync_file_modified_date_action.addItem( HC.content_modified_date_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_COPY ], HC.CONTENT_MERGE_ACTION_COPY )
            self._sync_notes_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_COPY ], HC.CONTENT_MERGE_ACTION_COPY )
            self._sync_notes_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_MOVE ], HC.CONTENT_MERGE_ACTION_MOVE )
            
        
        self._sync_urls_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ], HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        self._sync_file_modified_date_action.addItem( HC.content_modified_date_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ], HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        self._sync_notes_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ], HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        
        self._sync_note_import_options_button = ClientGUICommon.BetterButton( self, 'note merge settings', self._EditNoteImportOptions )
        
        #
        
        tag_service_options = duplicate_content_merge_options.GetTagServiceActions()
        rating_service_options = duplicate_content_merge_options.GetRatingServiceActions()
        sync_archive_action = duplicate_content_merge_options.GetSyncArchiveAction()
        sync_urls_action = duplicate_content_merge_options.GetSyncURLsAction()
        sync_file_modified_date_action = duplicate_content_merge_options.GetSyncFileModifiedDateAction()
        sync_notes_action = duplicate_content_merge_options.GetSyncNotesAction()
        self._sync_note_import_options = duplicate_content_merge_options.GetSyncNoteImportOptions()
        
        services_manager = HG.client_controller.services_manager
        
        self._service_keys_to_tag_options = { service_key : ( action, tag_filter ) for ( service_key, action, tag_filter ) in tag_service_options if services_manager.ServiceExists( service_key ) }
        
        self._tag_service_actions.SetData( list( self._service_keys_to_tag_options.keys() ) )
        
        self._tag_service_actions.Sort()
        
        self._service_keys_to_rating_options = { service_key : action for ( service_key, action ) in rating_service_options if services_manager.ServiceExists( service_key ) }
        
        self._rating_service_actions.SetData( list( self._service_keys_to_rating_options.keys() ) )
        
        self._rating_service_actions.Sort()
        
        self._sync_archive_action.SetValue( sync_archive_action )
        
        #
        
        if self._duplicate_action in ( HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE ) and not for_custom_action:
            
            self._sync_urls_action.setEnabled( False )
            self._sync_file_modified_date_action.setEnabled( False )
            self._sync_notes_action.setEnabled( False )
            
            self._sync_urls_action.SetValue( HC.CONTENT_MERGE_ACTION_NONE )
            self._sync_file_modified_date_action.SetValue( HC.CONTENT_MERGE_ACTION_NONE )
            self._sync_notes_action.SetValue( HC.CONTENT_MERGE_ACTION_NONE )
            
        else:
            
            self._sync_urls_action.SetValue( sync_urls_action )
            self._sync_file_modified_date_action.SetValue( sync_file_modified_date_action )
            self._sync_notes_action.SetValue( sync_notes_action )
            
        
        #
        
        tag_services_panel.Add( tag_services_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rating_services_panel.Add( rating_services_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, tag_services_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, rating_services_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        rows = []
        
        rows.append( ( 'sync archived status?: ', self._sync_archive_action ) )
        rows.append( ( 'sync file modified time?: ', self._sync_file_modified_date_action ) )
        rows.append( ( 'sync known urls?: ', self._sync_urls_action ) )
        rows.append( ( 'sync notes?: ', self._sync_notes_action ) )
        rows.append( ( '', self._sync_note_import_options_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        self._UpdateNoteControls()
        
        self._sync_notes_action.currentIndexChanged.connect( self._UpdateNoteControls )
        
    
    def _AddRating( self ):
        
        services_manager = HG.client_controller.services_manager
        
        choice_tuples = []
        
        for service in services_manager.GetServices( HC.RATINGS_SERVICES ):
            
            service_key = service.GetServiceKey()
            
            if service_key not in self._service_keys_to_rating_options:
                
                name = service.GetName()
                
                choice_tuples.append( ( name, service_key ) )
                
            
        
        if len( choice_tuples ) == 0:
            
            QW.QMessageBox.critical( self, 'Error', 'You have no more tag or rating services to add! Try editing the existing ones instead!' )
            
        else:
            
            try:
                
                service_key = ClientGUIDialogsQuick.SelectFromList( self, 'select service', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                service = services_manager.GetService( service_key )
                
                service_type = service.GetServiceType()
                
                if service_type == HC.LOCAL_RATING_INCDEC:
                    
                    str_lookup_dict = HC.content_number_merge_string_lookup
                    
                elif service_type in HC.STAR_RATINGS_SERVICES:
                    
                    str_lookup_dict = HC.content_merge_string_lookup
                    
                else:
                    
                    return
                    
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
                choice_tuples = [ ( str_lookup_dict[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            else:
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            self._service_keys_to_rating_options[ service_key ] = action
            
            self._rating_service_actions.AddDatas( ( service_key, ) )
            
            self._rating_service_actions.Sort()
            
        
    
    def _AddTag( self ):
        
        services_manager = HG.client_controller.services_manager
        
        choice_tuples = []
        
        for service in services_manager.GetServices( HC.REAL_TAG_SERVICES ):
            
            service_key = service.GetServiceKey()
            
            if service_key not in self._service_keys_to_tag_options:
                
                name = service.GetName()
                
                choice_tuples.append( ( name, service_key ) )
                
            
        
        if len( choice_tuples ) == 0:
            
            QW.QMessageBox.critical( self, 'Error', 'You have no more tag or rating services to add! Try editing the existing ones instead!' )
            
        else:
            
            try:
                
                service_key = ClientGUIDialogsQuick.SelectFromList( self, 'select service', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                service = services_manager.GetService( service_key )
                
                if service.GetServiceType() == HC.TAG_REPOSITORY:
                    
                    possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                    
                else:
                    
                    possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                    
                
                choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            else:
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            tag_filter = HydrusTags.TagFilter()
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
                
                namespaces = HG.client_controller.network_engine.domain_manager.GetParserNamespaces()
                
                panel = ClientGUITags.EditTagFilterPanel( dlg_3, tag_filter, namespaces = namespaces )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.exec() == QW.QDialog.Accepted:
                    
                    tag_filter = panel.GetValue()
                    
                    self._service_keys_to_tag_options[ service_key ] = ( action, tag_filter )
                    
                    self._tag_service_actions.AddDatas( ( service_key, ) )
                    
                    self._tag_service_actions.Sort()
                    
                
            
        
    
    def _ConvertRatingDataToListCtrlTuple( self, service_key ):
        
        action = self._service_keys_to_rating_options[ service_key ]
        
        try:
            
            service = HG.client_controller.services_manager.GetService( service_key )
            
            service_name = service.GetName()
            
            service_type = service.GetServiceType()
            
        except HydrusExceptions.DataMissing:
            
            service_name = 'missing service!'
            service_type = HC.LOCAL_RATING_LIKE
            
        
        if service_type == HC.LOCAL_RATING_INCDEC:
            
            str_lookup_dict = HC.content_number_merge_string_lookup
            
        else:
            
            str_lookup_dict = HC.content_merge_string_lookup
            
        
        pretty_action = str_lookup_dict[ action ]
        
        display_tuple = ( service_name, pretty_action )
        sort_tuple = ( service_name, pretty_action )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertTagDataToListCtrlTuple( self, service_key ):
        
        ( action, tag_filter ) = self._service_keys_to_tag_options[ service_key ]
        
        try:
            
            service_name = HG.client_controller.services_manager.GetName( service_key )
            
        except HydrusExceptions.DataMissing:
            
            service_name = 'missing service!'
            
        
        pretty_action = HC.content_merge_string_lookup[ action ]
        pretty_tag_filter = tag_filter.ToPermittedString()
        
        display_tuple = ( service_name, pretty_action, pretty_tag_filter )
        sort_tuple = ( service_name, pretty_action, pretty_tag_filter )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteRating( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            for service_key in self._rating_service_actions.GetData( only_selected = True ):
                
                del self._service_keys_to_rating_options[ service_key ]
                
            
            self._rating_service_actions.DeleteSelected()
            
        
    
    def _DeleteTag( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            for service_key in self._tag_service_actions.GetData( only_selected = True ):
                
                del self._service_keys_to_tag_options[ service_key ]
                
            
            self._tag_service_actions.DeleteSelected()
            
        
    
    def _EditNoteImportOptions( self ):
        
        allow_default_selection = False
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit note merge options' ) as dlg:
            
            panel = ClientGUIImportOptions.EditNoteImportOptionsPanel( dlg, self._sync_note_import_options, allow_default_selection, simple_mode = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._sync_note_import_options = panel.GetValue()
                
            
        
    
    def _EditRating( self ):
        
        service_keys = self._rating_service_actions.GetData( only_selected = True )
        
        for service_key in service_keys:
            
            action = self._service_keys_to_rating_options[ service_key ]
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
                service_type = service.GetServiceType()
                
                if service_type == HC.LOCAL_RATING_INCDEC:
                    
                    str_lookup_dict = HC.content_number_merge_string_lookup
                    
                elif service_type in HC.STAR_RATINGS_SERVICES:
                    
                    str_lookup_dict = HC.content_merge_string_lookup
                    
                else:
                    
                    return
                    
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
                choice_tuples = [ ( str_lookup_dict[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    break
                    
                
            else: # This shouldn't get fired because the edit button is hidden, but w/e
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            self._service_keys_to_rating_options[ service_key ] = action
            
            self._rating_service_actions.UpdateDatas( ( service_key, ) )
            
            self._rating_service_actions.Sort()
            
        
    
    def _EditTag( self ):
        
        service_keys = self._tag_service_actions.GetData( only_selected = True )
        
        for service_key in service_keys:
            
            ( action, tag_filter ) = self._service_keys_to_tag_options[ service_key ]
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
                choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    break
                    
                
            else:
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
                
                namespaces = HG.client_controller.network_engine.domain_manager.GetParserNamespaces()
                
                panel = ClientGUITags.EditTagFilterPanel( dlg_3, tag_filter, namespaces = namespaces )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.exec() == QW.QDialog.Accepted:
                    
                    tag_filter = panel.GetValue()
                    
                    self._service_keys_to_tag_options[ service_key ] = ( action, tag_filter )
                    
                    self._tag_service_actions.UpdateDatas( ( service_key, ) )
                    
                    self._tag_service_actions.Sort()
                    
                else:
                    
                    break
                    
                
            
        
    
    def _UpdateNoteControls( self ):
        
        sync_notes_action = self._sync_notes_action.GetValue()
        
        self._sync_note_import_options_button.setEnabled( sync_notes_action != HC.CONTENT_MERGE_ACTION_NONE )
        
    
    def GetValue( self ) -> ClientDuplicates.DuplicateContentMergeOptions:
        
        tag_service_actions = [ ( service_key, action, tag_filter ) for ( service_key, ( action, tag_filter ) ) in self._service_keys_to_tag_options.items() ]
        rating_service_actions = [ ( service_key, action ) for ( service_key, action ) in self._service_keys_to_rating_options.items() ]
        sync_archive_action = self._sync_archive_action.GetValue()
        sync_urls_action = self._sync_urls_action.GetValue()
        sync_file_modified_date_action = self._sync_file_modified_date_action.GetValue()
        sync_notes_action = self._sync_notes_action.GetValue()
        
        duplicate_content_merge_options = ClientDuplicates.DuplicateContentMergeOptions()
        
        duplicate_content_merge_options.SetTagServiceActions( tag_service_actions )
        duplicate_content_merge_options.SetRatingServiceActions( rating_service_actions )
        duplicate_content_merge_options.SetSyncArchiveAction( sync_archive_action )
        duplicate_content_merge_options.SetSyncURLsAction( sync_urls_action )
        duplicate_content_merge_options.SetSyncFileModifiedDateAction( sync_file_modified_date_action )
        duplicate_content_merge_options.SetSyncNotesAction( sync_notes_action )
        duplicate_content_merge_options.SetSyncNoteImportOptions( self._sync_note_import_options )
        
        return duplicate_content_merge_options
        
    
class EditFileNotesPanel( CAC.ApplicationCommandProcessorMixin, ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, names_to_notes: typing.Dict[ str, str ], name_to_start_on: typing.Optional[ str ] ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        CAC.ApplicationCommandProcessorMixin.__init__( self )
        
        self._original_names = set()
        
        self._notebook = QW.QTabWidget( self )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._notebook, ( 80, 14 ) )
        
        self._notebook.setMinimumSize( min_width, min_height )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._AddNote )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit current name', self._EditName )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete current note', self._DeleteNote )
        
        self._copy_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().copy, self._Copy )
        self._copy_button.setToolTip( 'Copy all notes to the clipboard.' )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( 'Paste from a copy from another notes dialog.' )
        
        #
        
        index_to_select = 0
        
        if len( names_to_notes ) == 0:
            
            self._AddNotePanel( 'notes', '' )
            
        else:
            
            names = sorted( names_to_notes.keys() )
            
            for ( i, name ) in enumerate( names ):
                
                if name == name_to_start_on:
                    
                    index_to_select = i
                    
                
                note = names_to_notes[ name ]
                
                self._original_names.add( name )
                
                self._AddNotePanel( name, note )
                
            
        
        self._notebook.setCurrentIndex( index_to_select )
        
        first_panel = self._notebook.currentWidget()
        
        ClientGUIFunctions.SetFocusLater( first_panel )
        
        if HG.client_controller.new_options.GetBoolean( 'start_note_editing_at_end' ):
            
            HG.client_controller.CallAfterQtSafe( first_panel, 'moving cursor to end', first_panel.moveCursor, QG.QTextCursor.End )
            
        else:
            
            HG.client_controller.CallAfterQtSafe( first_panel, 'moving cursor to start', first_panel.moveCursor, QG.QTextCursor.Start )
            
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button )
        QP.AddToLayout( button_hbox, self._edit_button )
        QP.AddToLayout( button_hbox, self._delete_button )
        QP.AddToLayout( button_hbox, self._copy_button )
        QP.AddToLayout( button_hbox, self._paste_button )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media' ] )
        
        self._notebook.tabBarDoubleClicked.connect( self._TabBarDoubleClicked )
        
    
    def _AddNote( self ):
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        existing_names = set( names_to_notes.keys() )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the name for the note.', allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                name = dlg.GetValue()
                
                name = HydrusData.GetNonDupeName( name, existing_names )
                
                self._AddNotePanel( name, '' )
                
            
        
    
    def _AddNotePanel( self, name, note ):
        
        control = QW.QPlainTextEdit( self._notebook )
        
        try:
            
            control.setPlainText( note )
            
        except:
            
            control.setPlainText( repr( note ) )
            
        
        self._notebook.addTab( control, name )
        
        self._notebook.setCurrentWidget( control )
        
        ClientGUIFunctions.SetFocusLater( control )
        
        HG.client_controller.CallAfterQtSafe( control, 'moving cursor to end', control.moveCursor, QG.QTextCursor.End )
        
        self._UpdateButtons()
        
    
    def _Copy( self ):
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        text = json.dumps( names_to_notes )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            names_and_notes = json.loads( raw_text )
            
            clean_names_and_notes = []
            
            if isinstance( names_and_notes, dict ):
                
                names_and_notes = list( names_and_notes.items() )
                
            
            for item in names_and_notes:
                
                if not isinstance( item, collections.abc.Collection ):
                    
                    continue
                    
                
                if len( item ) != 2:
                    
                    raise Exception( 'Not a two-tuple!' )
                    

                ( key, value ) = item
                
                if not isinstance( key, str ):
                    
                    raise Exception( 'Key not a string!' )
                    
                
                if not isinstance( value, str ):
                    
                    raise Exception( 'Value not a string!' )
                    
                
                clean_names_and_notes.append( item )
                
            
            names_and_notes = clean_names_and_notes
            
        except Exception as e:
            
            ClientGUIFunctions.PresentClipboardParseError( self, raw_text, 'JSON names and notes, either as an Object or a list of pairs', e )
            
            return
            
        
        ( existing_names_to_notes, deletee_names ) = self.GetValue()
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        
        note_import_options.SetIsDefault( False )
        note_import_options.SetExtendExistingNoteIfPossible( True )
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
        
        new_names_to_notes = note_import_options.GetUpdateeNamesToNotes( existing_names_to_notes, names_and_notes )
        
        existing_panel_names_to_widgets = { self._notebook.tabText( i ) : self._notebook.widget( i ) for i in range( self._notebook.count() ) }
        
        for ( name, note ) in new_names_to_notes.items():
            
            if name in existing_panel_names_to_widgets:
                
                control = existing_panel_names_to_widgets[ name ]
                
                try:
                    
                    control.setPlainText( note )
                    
                except:
                    
                    control.setPlainText( repr( note ) )
                    
                
            else:
                
                self._AddNotePanel( name, note )
                
            
        
    
    def _DeleteNote( self ):
        
        text = 'Delete this note?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.Accepted:
            
            index = self._notebook.currentIndex()
            
            panel = self._notebook.currentWidget()
            
            self._notebook.removeTab( index )
            
            panel.deleteLater()
            
            self._UpdateButtons()
            
        
    
    def _EditName( self, index = None ):
        
        if index is None:
            
            index = self._notebook.currentIndex()
            
        
        name = self._notebook.tabText( index )
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        existing_names = set( names_to_notes.keys() )
        
        existing_names.discard( name )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the name for the note.', allow_blank = False, default = name ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                name = dlg.GetValue()
                
                name = HydrusData.GetNonDupeName( name, existing_names )
                
                self._notebook.setTabText( index, name )
                
            
        
    
    def _TabBarDoubleClicked( self, index: int ):
        
        if index == -1:
            
            self._AddNote()
            
        else:
            
            self._EditName( index = index )
            
        
    
    def _UpdateButtons( self ):
        
        can_edit = self._notebook.count() > 0
        
        self._edit_button.setEnabled( can_edit )
        self._delete_button.setEnabled( can_edit )
        
    
    def GetValue( self ) -> typing.Tuple[ typing.Dict[ str, str ], typing.Set[ str ] ]:
        
        names_to_notes = { self._notebook.tabText( i ) : HydrusText.CleanNoteText( self._notebook.widget( i ).toPlainText() ) for i in range( self._notebook.count() ) }
        
        names_to_notes = { name : text for ( name, text ) in names_to_notes.items() if text != '' }
        
        deletee_names = { name for name in self._original_names if name not in names_to_notes }
        
        return ( names_to_notes, deletee_names )
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_NOTES:
                
                self._OKParent()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def UserIsOKToOK( self ):
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        empty_note_names = sorted( ( name for ( name, note ) in names_to_notes.items() if note == '' ) )
        
        if len( empty_note_names ) > 0:
            
            message = 'These notes are empty, and will not be saved--is this ok?'
            message += os.linesep * 2
            message += ', '.join( empty_note_names )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return False
                
            
        
        return True
        
    

class EditFileTimestampsPanel( CAC.ApplicationCommandProcessorMixin, ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, media: ClientMedia.MediaSingleton ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        CAC.ApplicationCommandProcessorMixin.__init__( self )
        
        self._media = media
        
        timestamps_manager = self._media.GetLocationsManager().GetTimestampsManager()
        
        #
        
        self._archive_timestamp = ClientGUITime.DateTimeButton( self, seconds_allowed = True, only_past_dates = True )
        self._file_modified_timestamp = ClientGUITime.DateTimeButton( self, seconds_allowed = True, only_past_dates = True )
        
        self._last_viewed_media_viewer_timestamp = ClientGUITime.DateTimeButton( self, seconds_allowed = True, only_past_dates = True )
        self._last_viewed_preview_viewer_timestamp = ClientGUITime.DateTimeButton( self, seconds_allowed = True, only_past_dates = True )
        
        self._file_modified_timestamp_warning_st = ClientGUICommon.BetterStaticText( self, label = 'initialising' )
        self._file_modified_timestamp_warning_st.setObjectName( 'HydrusWarning' )
        self._file_modified_timestamp_warning_st.setAlignment( QC.Qt.AlignCenter )
        self._file_modified_timestamp_warning_st.setVisible( False )
        
        domain_box = ClientGUICommon.StaticBox( self, 'web domain times' )
        
        self._domain_modified_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( domain_box )
        
        self._domain_modified_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._domain_modified_list_ctrl_panel, CGLC.COLUMN_LIST_DOMAIN_MODIFIED_TIMESTAMPS.ID, 8, self._ConvertTimestampDataToDomainModifiedListCtrlTuples, use_simple_delete = True, activation_callback = self._EditDomainModifiedTimestamp )
        
        self._domain_modified_list_ctrl_panel.SetListCtrl( self._domain_modified_list_ctrl )
        
        self._domain_modified_list_ctrl_panel.AddButton( 'add', self._AddDomainModifiedTimestamp )
        self._domain_modified_list_ctrl_panel.AddButton( 'edit', self._EditDomainModifiedTimestamp, enabled_only_on_selection = True )
        self._domain_modified_list_ctrl_panel.AddDeleteButton()
        
        file_services_box = ClientGUICommon.StaticBox( self, 'file services' )
        
        self._file_services_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( file_services_box )
        
        self._file_services_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._file_services_list_ctrl_panel, CGLC.COLUMN_LIST_FILE_SERVICE_TIMESTAMPS.ID, 8, self._ConvertTimestampDataToFileServiceListCtrlTuples, activation_callback = self._EditFileServiceTimestamp )
        
        self._file_services_list_ctrl_panel.SetListCtrl( self._file_services_list_ctrl )
        
        self._file_services_list_ctrl_panel.AddButton( 'edit', self._EditFileServiceTimestamp, enabled_only_on_selection = True )
        # TODO: An extension here is to add an 'add' button for files that have a _missing_ delete time
        
        #
        
        rows = []
        
        #
        
        file_modified_timestamp = timestamps_manager.GetFileModifiedTimestamp()
        
        if file_modified_timestamp is None:
            
            self._file_modified_timestamp.setEnabled( False )
            self._file_modified_timestamp.setText( 'unknown -- run file maintenance to determine' )
            
        else:
            
            self._file_modified_timestamp.SetValueTimestamp( file_modified_timestamp )
            
        
        rows.append( ( 'file modified time: ', self._file_modified_timestamp ) )
        
        rows.append( self._file_modified_timestamp_warning_st )
        
        #
        
        if not self._media.HasInbox():
            
            archived_timestamp = timestamps_manager.GetArchivedTimestamp()
            
            if archived_timestamp is not None:
                
                self._archive_timestamp.SetValueTimestamp( archived_timestamp )
                
            
            rows.append( ( 'archived time: ', self._archive_timestamp ) )
            
        else:
            
            self._archive_timestamp.setVisible( False )
            
        
        #
        
        last_viewed_media_viewer_timestamp = timestamps_manager.GetLastViewedTimestamp( CC.CANVAS_MEDIA_VIEWER )
        
        if last_viewed_media_viewer_timestamp is None:
            
            self._last_viewed_media_viewer_timestamp.setVisible( False )
            
        else:
            
            self._last_viewed_media_viewer_timestamp.SetValueTimestamp( last_viewed_media_viewer_timestamp )
            
            rows.append( ( 'last viewed in media viewer: ', self._last_viewed_media_viewer_timestamp ) )
            
        
        last_viewed_preview_viewer_timestamp = timestamps_manager.GetLastViewedTimestamp( CC.CANVAS_PREVIEW )
        
        if last_viewed_preview_viewer_timestamp is None:
            
            self._last_viewed_preview_viewer_timestamp.setVisible( False )
            
        else:
            
            self._last_viewed_preview_viewer_timestamp.SetValueTimestamp( last_viewed_preview_viewer_timestamp )
            
            rows.append( ( 'last viewed in preview viewer: ', self._last_viewed_preview_viewer_timestamp ) )
            
        
        #
        
        self._domain_modified_list_ctrl.AddDatas( timestamps_manager.GetDomainModifiedTimestampDatas() )
        self._domain_modified_list_ctrl.Sort()
        
        self._file_services_list_ctrl.AddDatas( timestamps_manager.GetFileServiceTimestampDatas() )
        self._file_services_list_ctrl.Sort()
        
        #
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'all times', 'Copy every time here for pasting in another file\'s dialog.', self._Copy ) )
        
        c = HydrusData.Call( self._Copy, allowed_timestamp_types = ( HC.TIMESTAMP_TYPE_IMPORTED, HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, HC.TIMESTAMP_TYPE_DELETED ) )
        
        menu_items.append( ( 'normal', 'all file service times', 'Copy every imported/deleted/previously imported time here for pasting in another file\'s dialog.', c ) )
        
        c = HydrusData.Call( self._Copy, allowed_timestamp_types = ( HC.TIMESTAMP_TYPE_IMPORTED, HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, HC.TIMESTAMP_TYPE_DELETED ), adjust_delta = 1 )
        
        menu_items.append( ( 'normal', 'all file service times, plus one second', 'This is an experiment, feel free to play around with it to manually force a certain order on a handful of files. I expect to replace it will a full \'cascade\' dialog in future.', c ) )
        
        self._copy_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().copy, menu_items )
        self._copy_button.setToolTip( 'Copy timestamps to the clipboard.' )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( 'Paste timestamps from another timestamps dialog.' )
        
        #
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        domain_box.Add( self._domain_modified_list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        file_services_box.Add( self._file_services_list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._copy_button )
        QP.AddToLayout( button_hbox, self._paste_button )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, domain_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, file_services_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media' ] )
        
        self._file_modified_timestamp.dateTimeChanged.connect( self._ShowFileModifiedWarning )
        
        ClientGUIFunctions.SetFocusLater( self )
        
    
    def _ConvertTimestampDataToDomainModifiedListCtrlTuples( self, timestamp_data: ClientTime.TimestampData ):
        
        domain = timestamp_data.location
        
        pretty_timestamp = HydrusTime.TimestampToPrettyTime( timestamp_data.timestamp )
        
        display_tuple = ( domain, pretty_timestamp )
        sort_tuple = ( domain, timestamp_data.timestamp )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertTimestampDataToFileServiceListCtrlTuples( self, timestamp_data: ClientTime.TimestampData ):
        
        try:
            
            pretty_name = HG.client_controller.services_manager.GetName( timestamp_data.location )
            
        except HydrusExceptions.DataMissing:
            
            pretty_name = 'unknown service!'
            
        
        sort_name = pretty_name
        
        pretty_timestamp_type = HC.timestamp_type_str_lookup[ timestamp_data.timestamp_type ]
        sort_timestamp_type = pretty_timestamp_type
        
        pretty_timestamp = HydrusTime.TimestampToPrettyTime( timestamp_data.timestamp )
        
        if timestamp_data.timestamp is None:
            
            sort_timestamp = 0
            
        else:
            
            sort_timestamp = timestamp_data.timestamp
            
        
        display_tuple = ( pretty_name, pretty_timestamp_type, pretty_timestamp )
        sort_tuple = ( sort_name, sort_timestamp_type, sort_timestamp )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Copy( self, allowed_timestamp_types = None, adjust_delta = 0 ):
        
        list_of_timestamp_data = self._GetValidTimestampDatas()
        
        if allowed_timestamp_types is not None:
            
            list_of_timestamp_data = [ timestamp_data for timestamp_data in list_of_timestamp_data if timestamp_data.timestamp_type in allowed_timestamp_types ]
            
        
        if adjust_delta != 0:
            
            for timestamp_data in list_of_timestamp_data:
                
                if timestamp_data.timestamp is not None:
                    
                    timestamp_data.timestamp += adjust_delta
                    
                
            
        
        list_of_timestamp_data = HydrusSerialisable.SerialisableList( list_of_timestamp_data )
        
        text = json.dumps( list_of_timestamp_data.GetSerialisableTuple() )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _AddDomainModifiedTimestamp( self ):
        
        message = 'Enter domain'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                domain = dlg.GetValue()
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit datetime' ) as dlg_2:
                    
                    panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_2 )
                    
                    control = ClientGUITime.DateTimeCtrl( self, seconds_allowed = True, none_allowed = False, only_past_dates = True )
                    
                    qt_datetime = QC.QDateTime.currentDateTime()
                    
                    control.SetValue( qt_datetime )
                    
                    panel.SetControl( control )
                    
                    dlg_2.SetPanel( panel )
                    
                    if dlg_2.exec() == QW.QDialog.Accepted:
                        
                        new_qt_datetime = control.GetValue()
                        
                        timestamp = new_qt_datetime.toSecsSinceEpoch()
                        
                        timestamp_data = ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN, location = domain, timestamp = timestamp )
                        
                        self._domain_modified_list_ctrl.AddDatas( ( timestamp_data, ) )
                        
                        self._domain_modified_list_ctrl.Sort()
                        
                    
                
            
        
    
    def _EditDomainModifiedTimestamp( self ):
        
        selected_timestamp_datas = self._domain_modified_list_ctrl.GetData( only_selected = True )
        
        for timestamp_data in selected_timestamp_datas:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit datetime' ) as dlg:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
                
                control = ClientGUITime.DateTimeCtrl( self, seconds_allowed = True, none_allowed = False, only_past_dates = True )
                
                qt_datetime = QC.QDateTime.fromSecsSinceEpoch( timestamp_data.timestamp )
                
                control.SetValue( qt_datetime )
                
                panel.SetControl( control )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    new_qt_datetime = control.GetValue()
                    
                    new_timestamp = new_qt_datetime.toSecsSinceEpoch()
                    
                    if new_timestamp != timestamp_data.timestamp:
                        
                        new_timestamp_data = timestamp_data.Duplicate()
                        
                        new_timestamp_data.timestamp = new_timestamp
                        
                        self._domain_modified_list_ctrl.DeleteDatas( ( timestamp_data, ) )
                        self._domain_modified_list_ctrl.AddDatas( ( new_timestamp_data, ) )
                        
                        self._domain_modified_list_ctrl.Sort()
                        
                    
                
            
        
    
    def _EditFileServiceTimestamp( self ):
        
        selected_timestamp_datas = self._file_services_list_ctrl.GetData( only_selected = True )
        
        for timestamp_data in selected_timestamp_datas:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit datetime' ) as dlg:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
                
                control = ClientGUITime.DateTimeCtrl( self, seconds_allowed = True, none_allowed = False, only_past_dates = True )
                
                qt_datetime = QC.QDateTime.fromSecsSinceEpoch( timestamp_data.timestamp )
                
                control.SetValue( qt_datetime )
                
                panel.SetControl( control )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    new_qt_datetime = control.GetValue()
                    
                    new_timestamp = new_qt_datetime.toSecsSinceEpoch()
                    
                    if new_timestamp != timestamp_data.timestamp:
                        
                        new_timestamp_data = timestamp_data.Duplicate()
                        
                        new_timestamp_data.timestamp = new_timestamp
                        
                        self._file_services_list_ctrl.DeleteDatas( ( timestamp_data, ) )
                        self._file_services_list_ctrl.AddDatas( ( new_timestamp_data, ) )
                        
                        self._file_services_list_ctrl.Sort()
                        
                    
                
            
        
    
    def _GetValidTimestampDatas( self, only_changes = False ) -> typing.List[ ClientTime.TimestampData ]:
        
        timestamps_manager = self._media.GetLocationsManager().GetTimestampsManager()
        
        result = []
        
        #
        
        if not self._media.HasInbox():
            
            archive_timestamp = self._archive_timestamp.GetValueTimestamp()
            
            we_want_it = archive_timestamp != timestamps_manager.GetArchivedTimestamp() or not only_changes
            
            if archive_timestamp is not None and we_want_it:
                
                result.append( ClientTime.TimestampData.STATICArchivedTime( archive_timestamp ) )
                
            
        
        #
        
        file_modified_timestamp = self._file_modified_timestamp.GetValueTimestamp()
        
        we_want_it = file_modified_timestamp != timestamps_manager.GetFileModifiedTimestamp() or not only_changes
        
        if file_modified_timestamp is not None and we_want_it:
            
            result.append( ClientTime.TimestampData.STATICFileModifiedTime( file_modified_timestamp ) )
            
        
        #
        
        last_viewed_media_viewer_timestamp = self._last_viewed_media_viewer_timestamp.GetValueTimestamp()
        
        we_want_it = last_viewed_media_viewer_timestamp != timestamps_manager.GetLastViewedTimestamp( CC.CANVAS_MEDIA_VIEWER ) or not only_changes
        
        if last_viewed_media_viewer_timestamp is not None and we_want_it:
            
            result.append( ClientTime.TimestampData.STATICLastViewedTime( CC.CANVAS_MEDIA_VIEWER, last_viewed_media_viewer_timestamp ) )
            
        
        last_viewed_preview_viewer_timestamp = self._last_viewed_preview_viewer_timestamp.GetValueTimestamp()
        
        we_want_it = last_viewed_preview_viewer_timestamp != timestamps_manager.GetLastViewedTimestamp( CC.CANVAS_PREVIEW ) or not only_changes
        
        if last_viewed_preview_viewer_timestamp is not None and we_want_it:
            
            result.append( ClientTime.TimestampData.STATICLastViewedTime( CC.CANVAS_PREVIEW, last_viewed_preview_viewer_timestamp ) )
            
        
        #
        
        new_domain_modified_timestamp_datas = self._domain_modified_list_ctrl.GetData()
        
        original_domain_modified_timestamp_datas = timestamps_manager.GetDomainModifiedTimestampDatas()
        
        if only_changes:
            
            result.extend( set( new_domain_modified_timestamp_datas ).difference( original_domain_modified_timestamp_datas ) )
            
        else:
            
            result.extend( new_domain_modified_timestamp_datas )
            
        
        original_domains = { timestamp_data.location for timestamp_data in original_domain_modified_timestamp_datas }
        new_domains = { timestamp_data.location for timestamp_data in new_domain_modified_timestamp_datas }
        
        deletee_timestamp_datas = [ ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN, location = domain, timestamp = None ) for domain in original_domains.difference( new_domains ) ]
        
        result.extend( deletee_timestamp_datas )
        
        #
        
        possibly_edited_file_service_timestamp_datas = self._file_services_list_ctrl.GetData()
        original_file_service_timestamp_datas = timestamps_manager.GetFileServiceTimestampDatas()
        
        for timestamp_data in possibly_edited_file_service_timestamp_datas:
            
            we_want_it = timestamp_data not in original_file_service_timestamp_datas or not only_changes
            
            if timestamp_data.timestamp is not None and we_want_it:
                
                result.append( timestamp_data )
                
            
        
        result = HydrusSerialisable.SerialisableList( result ).Duplicate()
        
        return result
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            serialisable_tuple = json.loads( raw_text )
            
            list_of_timestamp_data = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tuple )
            
            for item in list_of_timestamp_data:
                
                if not isinstance( item, ClientTime.TimestampData ):
                    
                    raise Exception( 'Not a timestamp data!' )
                    
                
            
        except Exception as e:
            
            ClientGUIFunctions.PresentClipboardParseError( self, raw_text, 'A list of JSON-serialised Timestamp Data objects', e )
            
            return
            
        
        self._SetValueTimestampDatas( list_of_timestamp_data )
        
    
    def _SetValueTimestampDatas( self, list_of_timestamp_data: typing.Collection[ ClientTime.TimestampData ] ):
        
        for timestamp_data in list_of_timestamp_data:
            
            if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_ARCHIVED:
                
                if self._media.HasInbox() or timestamp_data.timestamp is None:
                    
                    continue
                    
                
                self._archive_timestamp.SetValueTimestamp( timestamp_data.timestamp )
                
            elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE:
                
                if timestamp_data.timestamp is None:
                    
                    continue
                    
                
                self._file_modified_timestamp.SetValueTimestamp( timestamp_data.timestamp )
                
            elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
                
                if timestamp_data.location is None or timestamp_data.timestamp is None:
                    
                    continue
                    
                
                if timestamp_data.location == CC.CANVAS_MEDIA_VIEWER:
                    
                    if self._last_viewed_media_viewer_timestamp.isVisible():
                        
                        self._last_viewed_media_viewer_timestamp.SetValueTimestamp( timestamp_data.timestamp )
                        
                    
                elif timestamp_data.location == CC.CANVAS_PREVIEW:
                    
                    if self._last_viewed_preview_viewer_timestamp.isVisible():
                        
                        self._last_viewed_preview_viewer_timestamp.SetValueTimestamp( timestamp_data.timestamp )
                        
                    
                
            elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
                
                current_domain_modified_timestamp_datas = self._domain_modified_list_ctrl.GetData()
                
                for existing_timestamp_data in current_domain_modified_timestamp_datas:
                    
                    if existing_timestamp_data.location == timestamp_data.location:
                        
                        self._domain_modified_list_ctrl.DeleteDatas( ( existing_timestamp_data, ) )
                        
                        break
                        
                    
                
                if timestamp_data.timestamp is not None:
                    
                    self._domain_modified_list_ctrl.AddDatas( ( timestamp_data, ) )
                    
                
            elif timestamp_data.timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
                
                if timestamp_data.location is None or timestamp_data.timestamp is None:
                    
                    continue
                    
                
                current_file_service_timestamp_datas = self._file_services_list_ctrl.GetData()
                
                for existing_timestamp_data in current_file_service_timestamp_datas:
                    
                    if existing_timestamp_data.timestamp_type == timestamp_data.timestamp_type and existing_timestamp_data.location == timestamp_data.location:
                        
                        if existing_timestamp_data.timestamp != timestamp_data.timestamp:
                            
                            self._file_services_list_ctrl.DeleteDatas( ( existing_timestamp_data, ) )
                            self._file_services_list_ctrl.AddDatas( ( timestamp_data, ) )
                            
                            self._file_services_list_ctrl.Sort()
                            
                            break
                            
                        
                    
                
            
        
    
    def _ShowFileModifiedWarning( self ):
        
        for timestamp_data in self._GetValidTimestampDatas( only_changes = True ):
            
            if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE and timestamp_data.timestamp is not None:
                
                self._file_modified_timestamp_warning_st.setVisible( True )
                
                if HydrusPaths.FileModifiedTimeIsOk( timestamp_data.timestamp ):
                    
                    self._file_modified_timestamp_warning_st.setText( 'This will also change the modified time of the file on disk!' )
                    
                else:
                    
                    self._file_modified_timestamp_warning_st.setText( 'File modified time on disk will not be changed--the timestamp is too early.' )
                    
                
                return
                
            
        
        self._file_modified_timestamp_warning_st.setVisible( False )
        
    
    def GetFileModifiedUpdate( self ) -> typing.Optional[ int ]:
        
        for timestamp_data in self._GetValidTimestampDatas( only_changes = True ):
            
            if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE and timestamp_data.timestamp is not None:
                
                if HydrusPaths.FileModifiedTimeIsOk( timestamp_data.timestamp ):
                    
                    return timestamp_data.timestamp
                    
                
            
        
        return None
        
    
    def GetServiceKeysToContentUpdates( self ) -> typing.Dict[ bytes, typing.List[ HydrusData.ContentUpdate ] ]:
        
        content_updates = []
        
        for timestamp_data in self._GetValidTimestampDatas( only_changes = True ):
            
            if timestamp_data.timestamp is None:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_DELETE, ( self._media.GetHash(), timestamp_data ) )
                
            else:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( self._media.GetHash(), timestamp_data ) )
                
            
            content_updates.append( content_update )
            
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : content_updates }
        
        return service_keys_to_content_updates
        
    
    def GetValue( self ):
        
        return self.GetServiceKeysToContentUpdates()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_TIMESTAMPS:
                
                self._OKParent()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    

class EditFrameLocationPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, info ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_info = info
        
        self._remember_size = QW.QCheckBox( 'remember size', self )
        self._remember_position = QW.QCheckBox( 'remember position', self )
        
        self._last_size = ClientGUICommon.NoneableSpinCtrl( self, 'last size', none_phrase = 'none set', min = 100, max = 1000000, unit = None, num_dimensions = 2 )
        self._last_position = ClientGUICommon.NoneableSpinCtrl( self, 'last position', none_phrase = 'none set', min = -1000000, max = 1000000, unit = None, num_dimensions = 2 )
        
        self._default_gravity_x = ClientGUICommon.BetterChoice( self )
        
        self._default_gravity_x.addItem( 'by default, expand to width of parent', 1 )
        self._default_gravity_x.addItem( 'by default, expand width as much as needed', -1 )
        
        self._default_gravity_y = ClientGUICommon.BetterChoice( self )
        
        self._default_gravity_y.addItem( 'by default, expand to height of parent', 1 )
        self._default_gravity_y.addItem( 'by default, expand height as much as needed', -1 )
        
        self._default_position = ClientGUICommon.BetterChoice( self )
        
        self._default_position.addItem( 'by default, position off the top-left corner of parent', 'topleft')
        self._default_position.addItem( 'by default, position centered on the parent', 'center')
        
        self._maximised = QW.QCheckBox( 'start maximised', self )
        self._fullscreen = QW.QCheckBox( 'start fullscreen', self )
        
        #
        
        ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = self._original_info
        
        self._remember_size.setChecked( remember_size )
        self._remember_position.setChecked( remember_position )
        
        self._last_size.SetValue( last_size )
        self._last_position.SetValue( last_position )
        
        ( x, y ) = default_gravity
        
        self._default_gravity_x.SetValue( x )
        self._default_gravity_y.SetValue( y )
        
        self._default_position.SetValue( default_position )
        
        self._maximised.setChecked( maximised )
        self._fullscreen.setChecked( fullscreen )
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'Setting frame location info for ' + name + '.'
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._remember_size, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._remember_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._last_size, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._last_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._default_gravity_x, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._default_gravity_y, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._default_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._maximised, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._fullscreen, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = self._original_info
        
        remember_size = self._remember_size.isChecked()
        remember_position = self._remember_position.isChecked()
        
        last_size = self._last_size.GetValue()
        last_position = self._last_position.GetValue()
        
        x = self._default_gravity_x.GetValue()
        y = self._default_gravity_y.GetValue()
        
        default_gravity = [ x, y ]
        
        default_position = self._default_position.GetValue()
        
        maximised = self._maximised.isChecked()
        fullscreen = self._fullscreen.isChecked()
        
        return ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
        
    
class EditMediaViewOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, info ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_info = info
        
        ( self._mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) ) = self._original_info
        
        ( possible_show_actions, can_start_paused, can_start_with_embed ) = CC.media_viewer_capabilities[ self._mime ]
        
        self._media_show_action = ClientGUICommon.BetterChoice( self )
        self._media_start_paused = QW.QCheckBox( self )
        self._media_start_with_embed = QW.QCheckBox( self )
        self._preview_show_action = ClientGUICommon.BetterChoice( self )
        self._preview_start_paused = QW.QCheckBox( self )
        self._preview_start_with_embed = QW.QCheckBox( self )
        
        advanced_mode = HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        for action in possible_show_actions:
            
            if action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV and not ClientGUIMPV.MPV_IS_AVAILABLE:
                
                continue
                
            
            simple_mode = not advanced_mode
            not_source = not HC.RUNNING_FROM_SOURCE
            not_qt_6 = not QtInit.WE_ARE_QT6
            
            if action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER and ( simple_mode or not_source or not_qt_6 ):
                
                continue
                
            
            s = CC.media_viewer_action_string_lookup[ action ]
            
            if action in ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER ) and self._mime in ( HC.IMAGE_GIF, HC.GENERAL_ANIMATION ):
                
                s += ' (will show unanimated gifs with native viewer)'
                
            
            if action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE and self._mime in [ HC.GENERAL_VIDEO ] + list( HC.VIDEO ):
                
                s += ' (no audio support)'
                
            
            self._media_show_action.addItem( s, action )
            
            if action != CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY:
                
                self._preview_show_action.addItem( s, action )
                
            
        
        self._media_show_action.currentIndexChanged.connect( self.EventActionChange )
        self._preview_show_action.currentIndexChanged.connect( self.EventActionChange )
        
        self._media_scale_up = ClientGUICommon.BetterChoice( self )
        self._media_scale_down = ClientGUICommon.BetterChoice( self )
        self._preview_scale_up = ClientGUICommon.BetterChoice( self )
        self._preview_scale_down = ClientGUICommon.BetterChoice( self )
        
        for scale_action in ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_TO_CANVAS ):
            
            text = CC.media_viewer_scale_string_lookup[ scale_action ]
            
            self._media_scale_up.addItem( text, scale_action )
            self._preview_scale_up.addItem( text, scale_action )
            
            self._media_scale_down.addItem( text, scale_action )
            self._preview_scale_down.addItem( text, scale_action )
            
        
        self._exact_zooms_only = QW.QCheckBox( 'only permit half and double zooms', self )
        self._exact_zooms_only.setToolTip( 'This limits zooms to 25%, 50%, 100%, 200%, 400%, and so on. It makes for fast resize and is useful for files that often have flat colours and hard edges, which often scale badly otherwise. The \'canvas fit\' zoom will still be inserted.' )
        
        self._scale_up_quality = ClientGUICommon.BetterChoice( self )
        
        for zoom in ( CC.ZOOM_NEAREST, CC.ZOOM_LINEAR, CC.ZOOM_CUBIC, CC.ZOOM_LANCZOS4 ):
            
            self._scale_up_quality.addItem( CC.zoom_string_lookup[ zoom], zoom )
            
        
        self._scale_down_quality = ClientGUICommon.BetterChoice( self )
        
        for zoom in ( CC.ZOOM_NEAREST, CC.ZOOM_LINEAR, CC.ZOOM_AREA ):
            
            self._scale_down_quality.addItem( CC.zoom_string_lookup[ zoom], zoom )
            
        
        #
        
        self._media_show_action.SetValue( media_show_action )
        self._media_start_paused.setChecked( media_start_paused )
        self._media_start_with_embed.setChecked( media_start_with_embed )
        
        self._preview_show_action.SetValue( preview_show_action )
        self._preview_start_paused.setChecked( preview_start_paused )
        self._preview_start_with_embed.setChecked( preview_start_with_embed )
        
        self._media_scale_up.SetValue( media_scale_up )
        self._media_scale_down.SetValue( media_scale_down )
        self._preview_scale_up.SetValue( preview_scale_up )
        self._preview_scale_down.SetValue( preview_scale_down )
        
        self._exact_zooms_only.setChecked( exact_zooms_only )
        
        self._scale_up_quality.SetValue( scale_up_quality )
        self._scale_down_quality.SetValue( scale_down_quality )
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'Setting media view options for ' + HC.mime_string_lookup[ self._mime ] + '.'
        
        if not ClientGUIMPV.MPV_IS_AVAILABLE:
            
            text += ' MPV is not available for this client.'
            
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'media viewer show action: ', self._media_show_action ) )
        rows.append( ( 'media starts paused: ', self._media_start_paused ) )
        rows.append( ( 'media starts covered with an embed button: ', self._media_start_with_embed ) )
        rows.append( ( 'preview viewer show action: ', self._preview_show_action ) )
        rows.append( ( 'preview starts paused: ', self._preview_start_paused ) )
        rows.append( ( 'preview starts covered with an embed button: ', self._preview_start_with_embed ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if set( possible_show_actions ).isdisjoint( { CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER } ):
            
            self._media_scale_up.hide()
            self._media_scale_down.hide()
            self._preview_scale_up.hide()
            self._preview_scale_down.hide()
            
            self._exact_zooms_only.setVisible( False )
            
            self._scale_up_quality.hide()
            self._scale_down_quality.hide()
            
        else:
            
            rows = []
            
            rows.append( ( 'if the media is smaller than the media viewer canvas: ', self._media_scale_up ) )
            rows.append( ( 'if the media is larger than the media viewer canvas: ', self._media_scale_down ) )
            rows.append( ( 'if the media is smaller than the preview canvas: ', self._preview_scale_up) )
            rows.append( ( 'if the media is larger than the preview canvas: ', self._preview_scale_down ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, self._exact_zooms_only, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, 'Nearest neighbour is fast and ugly, 8x8 lanczos and area resampling are slower but beautiful.' ), CC.FLAGS_CENTER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._scale_up_quality, self, '>100% (interpolation) quality:' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._scale_down_quality, self, '<100% (decimation) quality:' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        if self._mime == HC.APPLICATION_FLASH:
            
            self._scale_up_quality.setEnabled( False )
            self._scale_down_quality.setEnabled( False )
            
        
        self.widget().setLayout( vbox )
        
        self._UpdateControls()
        
    
    def _UpdateControls( self ):
        
        media_ok = self._media_show_action.GetValue() not in CC.unsupported_media_actions
        preview_ok = self._preview_show_action.GetValue() not in CC.unsupported_media_actions
        
        if media_ok or preview_ok:
            
            self._exact_zooms_only.setEnabled( True )
            
            self._scale_up_quality.setEnabled( True )
            self._scale_down_quality.setEnabled( True )
            
        else:
            
            self._exact_zooms_only.setEnabled( False )
            
            self._scale_up_quality.setEnabled( False )
            self._scale_down_quality.setEnabled( False )
            
        
        if media_ok:
            
            self._media_scale_up.setEnabled( True )
            self._media_scale_down.setEnabled( True )
            
            self._media_start_paused.setEnabled( True )
            self._media_start_with_embed.setEnabled( True )
            
        else:
            
            self._media_scale_up.setEnabled( False )
            self._media_scale_down.setEnabled( False )
            
            self._media_start_paused.setEnabled( False )
            self._media_start_with_embed.setEnabled( False )
            
        
        if preview_ok:
            
            self._preview_scale_up.setEnabled( True )
            self._preview_scale_down.setEnabled( True )
            
            self._preview_start_paused.setEnabled( True )
            self._preview_start_with_embed.setEnabled( True )
            
        else:
            
            self._preview_scale_up.setEnabled( False )
            self._preview_scale_down.setEnabled( False )
            
            self._preview_start_paused.setEnabled( False )
            self._preview_start_with_embed.setEnabled( False )
            
        
        is_application = self._mime == HC.GENERAL_APPLICATION or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_APPLICATION ]
        is_image = self._mime == HC.GENERAL_IMAGE or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_IMAGE ]
        is_audio = self._mime == HC.GENERAL_AUDIO or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_AUDIO ]
        
        if not is_image:
            
            self._scale_up_quality.setEnabled( False )
            self._scale_down_quality.setEnabled( False )
            
        
        if is_image or is_application:
            
            self._media_start_paused.setEnabled( False )
            self._preview_start_paused.setEnabled( False )
            
        
        if is_audio:
            
            self._media_scale_up.setEnabled( False )
            self._media_scale_down.setEnabled( False )
            self._preview_scale_up.setEnabled( False )
            self._preview_scale_down.setEnabled( False )
            
        
    
    def EventActionChange( self, index ):
        
        self._UpdateControls()
        
    
    def GetValue( self ):
        
        media_show_action = self._media_show_action.GetValue()
        media_start_paused = self._media_start_paused.isChecked()
        media_start_with_embed = self._media_start_with_embed.isChecked()
        
        preview_show_action = self._preview_show_action.GetValue()
        preview_start_paused = self._preview_start_paused.isChecked()
        preview_start_with_embed = self._preview_start_with_embed.isChecked()
        
        media_scale_up = self._media_scale_up.GetValue()
        media_scale_down = self._media_scale_down.GetValue()
        preview_scale_up = self._preview_scale_up.GetValue()
        preview_scale_down = self._preview_scale_down.GetValue()
        
        exact_zooms_only = self._exact_zooms_only.isChecked()
        
        scale_up_quality = self._scale_up_quality.GetValue()
        scale_down_quality = self._scale_down_quality.GetValue()
        
        zoom_info = ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality )
        
        return ( self._mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info )
        
    
class EditNoneableIntegerPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, value: HC.noneable_int, message = '', none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1, num_dimensions = 1 ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._value = ClientGUICommon.NoneableSpinCtrl( self, message = message, none_phrase = none_phrase, min = min, max = max, unit = unit, multiplier = multiplier, num_dimensions = num_dimensions )
        
        self._value.SetValue( value )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._value, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ) -> HC.noneable_int:
        
        return self._value.GetValue()
        
    
class EditRegexFavourites( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, regex_favourites ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        regex_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._regexes = ClientGUIListCtrl.BetterListCtrl( regex_listctrl_panel, CGLC.COLUMN_LIST_REGEX_FAVOURITES.ID, 8, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        regex_listctrl_panel.SetListCtrl( self._regexes )
        
        regex_listctrl_panel.AddButton( 'add', self._Add )
        regex_listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        regex_listctrl_panel.AddDeleteButton()
        
        #
        
        self._regexes.SetData( regex_favourites )
        
        self._regexes.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, regex_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        current_data = self._regexes.GetData()
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter regex.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                regex_phrase = dlg.GetValue()
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter description.' ) as dlg_2:
                    
                    if dlg_2.exec() == QW.QDialog.Accepted:
                        
                        description = dlg_2.GetValue()
                        
                        row = ( regex_phrase, description )
                        
                        if row in current_data:
                            
                            QW.QMessageBox.warning( self, 'Warning', 'That regex and description are already in the list!' )
                            
                            return
                            
                        
                        self._regexes.AddDatas( ( row, ) )
                        
                    
                
            
        
    
    def _ConvertDataToListCtrlTuples( self, row ):
        
        ( regex_phrase, description ) = row
        
        display_tuple = ( regex_phrase, description )
        sort_tuple = ( regex_phrase, description )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        edited_datas = []
        
        rows = self._regexes.GetData( only_selected = True )
        
        for row in rows:
            
            ( regex_phrase, description ) = row
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Update regex.', default = regex_phrase ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    regex_phrase = dlg.GetValue()
                    
                    with ClientGUIDialogs.DialogTextEntry( self, 'Update description.', default = description ) as dlg_2:
                        
                        if dlg_2.exec() == QW.QDialog.Accepted:
                            
                            description = dlg_2.GetValue()
                            
                            edited_row = ( regex_phrase, description )
                            
                            self._regexes.DeleteDatas( ( row, ) )
                            
                            self._regexes.AddDatas( ( edited_row, ) )
                            
                            edited_datas.append( edited_row )
                            
                        
                    
                else:
                    
                    break
                    
                
            
        
        self._regexes.SelectDatas( edited_datas )
        
        self._regexes.Sort()
        
    
    def GetValue( self ):
        
        return self._regexes.GetData()
        
    
class EditSelectFromListPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, choice_tuples: list, value_to_select = None, sort_tuples = True ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._list = QW.QListWidget( self )
        self._list.itemDoubleClicked.connect( self.EventSelect )
        
        #
        
        selected_a_value = False
        
        if sort_tuples:
            
            try:
                
                choice_tuples.sort()
                
            except TypeError:
                
                try:
                    
                    choice_tuples.sort( key = lambda t: t[0] )
                    
                except TypeError:
                    
                    pass # fugg
                    
                
            
        
        for ( i, ( label, value ) ) in enumerate( choice_tuples ):
            
            item = QW.QListWidgetItem()
            item.setText( label )
            item.setData( QC.Qt.UserRole, value )
            self._list.addItem( item )
            
            if value_to_select is not None and value_to_select == value:
                
                QP.ListWidgetSetSelection( self._list, i )
                
                selected_a_value = True
                
            
        
        if not selected_a_value:
            
            QP.ListWidgetSetSelection( self._list, 0 )
            
        
        #
        
        max_label_width_chars = max( ( len( label ) for ( label, value ) in choice_tuples ) )
        
        width_chars = min( 64, max_label_width_chars + 2 )
        height_chars = min( max( 6, len( choice_tuples ) ), 36 )
        
        ( width_px, height_px ) = ClientGUIFunctions.ConvertTextToPixels( self._list, ( width_chars, height_chars ) )
        
        row_height_px = self._list.sizeHintForRow( 0 )
        
        if row_height_px != -1:
            
            height_px = row_height_px * height_chars
            
        
        # wew lad, but it 'works'
        # formalise this and make a 'stretchy qlistwidget' class
        self._list.sizeHint = lambda: QC.QSize( width_px, height_px )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def EventSelect( self, item ):
        
        self.parentWidget().DoOK()
        
    
    def GetValue( self ):
        
        selection = QP.ListWidgetGetSelection( self._list ) 
        
        return QP.GetClientData( self._list, selection )
        
    
class EditSelectFromListButtonsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, choices, message = '' ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._data = None
        
        vbox = QP.VBoxLayout()
        
        if message != '':
            
            st = ClientGUICommon.BetterStaticText( self, label = message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        first_focused = False
        
        for ( text, data, tooltip ) in choices:
            
            button = ClientGUICommon.BetterButton( self, text, self._ButtonChoice, data )
            
            button.setToolTip( tooltip )
            
            QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            if not first_focused:
                
                ClientGUIFunctions.SetFocusLater( button )
                
                first_focused = True
                
            
        
        self.widget().setLayout( vbox )
        
    
    def _ButtonChoice( self, data ):
        
        self._data = data
        
        self.parentWidget().DoOK()
        
    
    def GetValue( self ):
        
        return self._data
        
