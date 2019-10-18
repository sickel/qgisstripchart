# -*- coding: utf-8 -*-
"""
/***************************************************************************
 StripChart
                                 A QGIS plugin
 Draws a strip chart for a value over a layer
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-10-13
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Morten Sickel
        email                : morten@sickel.net
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the DockWidget
from .stripchart_dockwidget import StripChartDockWidget
import os.path

from qgis.PyQt.QtGui import QPen
from qgis.core import QgsProject, Qgis, QgsFeatureRequest
from qgis.PyQt.QtWidgets import QGraphicsScene,QApplication,QGraphicsView


class StripChart:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'StripChart_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Draw stripchart')
        self.toolbar = self.iface.addToolBar(u'Stripchart')
        self.toolbar.setObjectName(u'Stripchart')

        #print "** INITIALIZING StripChart"
        self.view = MouseReadGraphicsView(self.iface)
        self.view.layer=None
        self.pluginIsActive = False
        # self.dockwidget = None


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Stripchart', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToDatabaseMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/stripchart/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Stripcharts'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.dlg=StripChartDockWidget(self.iface.mainWindow())
        self.view.setParent(self.dlg) 
        self.dlg.vlMain.addWidget(self.view)
        self.scene=QGraphicsScene()
        self.view.setScene(self.scene)
        self.scene.setSceneRect(0,0,300,2000)
        self.setuplayers()
        self.init=False
            


    #--------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING StripChart"

        # disconnects
        self.dlg.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD StripChart"

        for action in self.actions:
            self.iface.removePluginDatabaseMenu(
                self.tr(u'&Draw strip chart'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    #--------------------------------------------------------------------------


    def listfields(self):
        # When selecting a new layer. List fields for that layer
        self.dlg.cbItem.clear()
        layername=self.dlg.cbLayer.currentText()
        layers = QgsProject.instance().mapLayersByName(layername) # list of layers with any name
        if len(layers)==0:
            return
        self.view.layer = layers[0] # first layer .
        fields = self.view.layer.fields().names() #Get Fields
        # Should only add relevant (i.e. numeric fields)
        self.dlg.cbItem.addItems(fields) #Added to the comboBox
    

    def stripchart(self):
        #self.iface.messageBar().pushMessage(
        #            "Info", "So far so good...",
        #            level=Qgis.Info, duration=3) # Info, Warning, Critical, Success
        #if self.init:
        #    return
        layername=self.dlg.cbLayer.currentText()
        layers = QgsProject.instance().mapLayersByName(layername) # list of layers with selected name
        if len(layers)==0:
            return
        self.view.layer = layers[0] # first layer 
        self.view.ids=[] # Keeps the ids .
        fieldname=self.dlg.cbItem.currentText()
        if fieldname=='' or fieldname is None:
            return
        values=[]
        request = QgsFeatureRequest().addOrderBy('Id').setFlags(QgsFeatureRequest.NoGeometry).setSubsetOfAttributes([self.view.idfield,fieldname], self.view.layer.fields() )
        iter=self.view.layer.getFeatures(request)
        for feature in iter:
            if isinstance(feature[fieldname],list):
                 self.iface.messageBar().pushMessage(
                    "Error", "Invalid field type : {}".format(fieldname),
                    level=Qgis.Warning, duration=3) # Info, Warning, Critical, Success
                 return
            values.append(feature[fieldname]) 
            self.view.ids.append(feature[self.view.idfield])  
        self.scene.setSceneRect(0,0,self.view.width,len(values))
        #self.iface.messageBar().pushMessage(
        #            "Info", "So far, so good {}",format(len(values)),
        #            level=Qgis.Info, duration=3) # Info, Warning, Critical, Success
        self.scene.clear()
        maxval=max(values)
        minval=min(values)
        # TODO: Make a sensible scaling using min and maxval
        scale=self.view.width/maxval
        n=0
        for v in values:
            self.scene.addLine(0,n,v*scale,n)
            n+=1
        
    def setuplayers(self):
        layers = QgsProject.instance().layerTreeRoot().children()
        self.dlg.cbLayer.clear()
        for layer in layers:
        # TODO: Filter so only vector layers are listed
            # if layer.layer()type==QgsMapLayer.Vectorlayer: - returns nothing...?
                self.dlg.cbLayer.addItems([layer.name()])
        self.listfields()
        

    def run(self):
        """Run method that loads and starts the plugin"""
        self.init=True
        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING StripChart"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            #if self.dockwidget == None:
            #    # Create the dockwidget (after translation) and keep reference
            #    self.dockwidget = StripChartDockWidget()
            
            

            # connect to provide cleanup on closing of dockwidget
            self.dlg.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.mainWindow().addDockWidget(Qt.RightDockWidgetArea, self.dlg)
            self.dlg.cbLayer.currentIndexChanged['QString'].connect(self.listfields)
            self.dlg.cbItem.currentIndexChanged['QString'].connect(self.stripchart)
            self.iface.mapCanvas().selectionChanged.connect(self.markselected)
            self.dlg.show()
            
    def markselected(self):
        sels=self.view.layer.selectedFeatures() # The selected features in the active (from this plugin's point of view) layer
        n=len(sels)
        self.view.clearselection()
        if n>0:
            self.view.markselection(sels)

class MouseReadGraphicsView(QGraphicsView):
    def __init__(self, iface):
        self.iface = iface
        QGraphicsView.__init__(self)
        self.selectlines=[]
        self.ids=[]
        self.width=250
        self.idfield='id' # Needs to be userselectable or autoset
        
    def selectmarker(self,y):
        selectpen=QPen(Qt.yellow)
        markline=self.scene().addLine(0,y,250,y,selectpen)
        markline.setZValue(-1)
        self.selectlines.append(markline)
    
    def clearselection(self):
        for line in self.selectlines:
             self.scene().removeItem(line)
        
    def markselection(self,sels):
        for sel in sels:
            idval=sel[self.idfield]
            y=self.ids.index(idval)
            self.selectmarker(y)
        
    #TODO - handle ctrl and/or shift click and drags correctly
    def mousePressEvent(self, event):
        if event.button() == 1:
            coords=self.mapToScene(event.pos())    
            self.ypress=coords.y()
            if self.layer== None:
                self.iface.messageBar().pushMessage(
                    "Clicked", "y: {} ".format(str(self.ypress),
                   level=Qgis.Info, duration=3)) # Info, Warning, Critical, Success
                return
            # self.selectmarker(y) # Do not need any longer. Changes in selection redraws
            return
            request = QgsFeatureRequest().addOrderBy('Id').setFlags(QgsFeatureRequest.NoGeometry).setSubsetOfAttributes([self.idfield], self.layer.fields() )
            iter=self.layer.getFeatures(request)
            n=0
            #DONE: Mark selected features in stripchart 
            
            for feature in iter:
                n=n+1
                if n < self.y:
                    next
                if n==self.y:
                    self.layer.select(feature[self.idfield])
                    
                    
    def mouseReleaseEvent(self, event):
        #if event.button() == 1:
            coords=self.mapToScene(event.pos())    
            yrelease=coords.y()
            if yrelease==None:
                yrelease=0
            if self.ypress==None:
                self.ypress=0
            if self.layer== None:
                self.iface.messageBar().pushMessage(
                    "Clicked", "y: {} ".format(str(y),
                   level=Qgis.Info, duration=3)) # Info, Warning, Critical, Success
                return
            # self.selectmarker(y) # Do not need any longer. Changes in selection redraws
            ymin=int(min(yrelease,self.ypress))
            ymax=int(max(yrelease,self.ypress))
            if ymin==ymax:
                ymax+=1
            selectedids=self.ids[ymin:ymax]
            self.layer.select(selectedids)
            return # Should not need the following...
            request = QgsFeatureRequest().addOrderBy('Id').setFlags(QgsFeatureRequest.NoGeometry).setSubsetOfAttributes([self.idfield], self.layer.fields() )
            iter=self.layer.getFeatures(request)
            n=0
            #DONE: Mark selected features in stripchart 
            for feature in iter:
                n=n+1
                if n < ymin:
                    next
                if n>=ymin and n <=ymax:
                    self.layer.select(feature[self.idfield])
