import glob
import os
import sys
import shutil
import struct
import tempfile
import re
import datetime
import threading
import time
import math
import configparser

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import font
from tkinter import Menu
from tkinter.messagebox import showinfo, showwarning, showerror
from tkinter.font import nametofont

import tkintermapview

from enum import Enum
from platformdirs import user_data_dir

from pathlib import Path, PurePath
from zipfile import ZipFile

class MotorStatus(Enum):
  UNKNOWN = 'Unknown'
  OFF = 'Off'
  IDLE = 'Idle'
  LIFT = 'Flying'


class SelectableMetrics(Enum):
  BASIC = 'Basic'
  ADVANCED = 'Advanced'
  DIAGNOSTICS = 'Diagnostics'


class SelectableTileServer(Enum):
  OPENSTREETMAP = 'OpenStreetMap'
  GOOGLE_STANDARD = 'Google Standard'
  GOOGLE_SATELLITE = 'Google Satellite'
  OPEN_TOPO = 'Open Topo'


class SelectablePlaybackSpeeds(Enum):
  REALTIME = 'Real-Time'
  FAST = 'Fast'
  FAST2 = 'Fast 2x'
  FAST4 = 'Fast 4x'
  FAST8 = 'Fast 8x'
  FAST16 = 'Fast 16x'
  FAST32 = 'Fast 32x'


class ExtractFlightData(tk.Tk):


  '''
  Global variables and constants.
  '''
  version = "v1.4.2"
  smallScreen = False
  tinyScreen = False
  scale = 1
  cpl = 137 # 137.84615384615384 characters fit on development machine screen.
  defaultDroneZoom = 18
  defaultBlankMapZoom = 1
  ctrlMarkerColor1  = ["#3880f5", "#4b4b4b", "#aaccf6", "#c8c8c8"]
  ctrlMarkerColor2  = ["#aaccf6", "#c8c8c8", "#3880f5", "#4b4b4b"]
  homeMarkerColor1  = ["#dc5145", "#4040ff", "#e49781", "#00ffff"]
  homeMarkerColor2  = ["#e49781", "#00ffff", "#dc5145", "#4040ff"]
  droneMarkerColor1 = ["#d98d00", "#008000", "#c6dfb3", "#00ff00"]
  droneMarkerColor2 = ["#c6dfb3", "#00ff00", "#d98d00", "#008000"]
  markerLabelColor  = ["#c0c0c0", "#ffc1ff", "#3c3c3c", "#575757"]
  pathColors = [
    ["#417dd6","#ab27a9","#e54f14","#ffa900","#00a31f"],
    ["#c6c6c6","#cfcfcf","#e0e0e0","#4c4c4c","#2d2d2d"],
    ["#ffed49","#ffcb00","#ffa800","#ff6e2c","#fa5b46"],
    ["#ff0000","#aad2fa","#0000ff","#ffff00","#000000","#ffffff"],
    ["#aad2fa","#0000ff","#ffff00","#000000","#ffffff","#ff0000"],
    ["#0000ff","#ffff00","#000000","#ffffff","#ff0000","#aad2fa"],
    ["#ffff00","#000000","#ffffff","#ff0000","#aad2fa","#0000ff"],
    ["#000000","#ffffff","#ff0000","#aad2fa","#0000ff","#ffff00"],
    ["#ffffff","#ff0000","#aad2fa","#0000ff","#ffff00","#000000"]
  ]
  displayMode = "ATOM"
  columns = ('recnum', 'recid', 'flight','timestamp','tod','time','flightstatus','distance1','dist1lat','dist1lon','distance2','dist2lat','dist2lon','distance3','altitude1','altitude2','speed1','speed1lat','speed1lon','speed2','speed2lat','speed2lon','speed1vert','speed2vert','satellites','ctrllat','ctrllon','homelat','homelon','dronelat','dronelon','rssi','channel','flightctrlconnected','remoteconnected','gps','inuse','motor1status','motor2status','motor3status','motor4status')
  showColsBasicAtom = ('flight','tod','time','flightstatus','distance3','altitude2','speed2','speed2vert','satellites','ctrllat','ctrllon','homelat','homelon','dronelat','dronelon','rssi','flightctrlconnected','gps')
  showColsAdvAtom = ('flight','tod','time','flightstatus','distance2','distance3','altitude1','altitude2','speed1','speed2','speed1vert','speed2vert','satellites','ctrllat','ctrllon','homelat','homelon','dronelat','dronelon','rssi','flightctrlconnected','gps','rssi','remoteconnected')
  showColsBasicDreamer = ('flight','tod','time','altitude1','distance1','satellites','homelat','homelon','dronelat','dronelon')
  showColsAdvDreamer = ('flight','tod','time','altitude1','distance1','satellites','homelat','homelon','dronelat','dronelon')
  zipFilename = None
  tree = None
  map_widget = None
  flightPaths = None
  pathCoords = None
  flightStarts = None
  ctrlmarker = None
  homemarker = None
  dronemarker = None
  ctrllabel = None
  homelabel = None
  dronelabel = None
  isPlaying = False
  currentRow = None
  labelFlight = None
  selectedPlaySpeed = None
  selectedTile = None
  selectPath = None
  selectedPath = None
  pathWidth = None
  imperial = None
  defaultDataRows = None
  rounded = None
  marketColorSet = None
  pathColorSet = None
  showMarkerCtrl = None
  showMarkerHome = None
  showPath = None
  selectedTableView = None
  labelFile = None
  userPath = None
  configParser = None
  configFilename = 'extractFlightData.ini'
  configPath = None
  defaultFontsize = 13 # 13 is default font size on development machine.
  lastFrameTs = None
  flightStats = None


  '''
  Calculate distance between 2 sets of coordinates (lat/lon). Used for sanity checking, i.e. handle bad GPS data.
  '''
  def haversine(self, lat1: float, long1: float, lat2: float, long2: float):
    degree_to_rad = float(math.pi / 180.0)
    d_lat = (lat2 - lat1) * degree_to_rad
    d_long = (long2 - long1) * degree_to_rad
    a = pow(math.sin(d_lat / 2), 2) + math.cos(lat1 * degree_to_rad) * math.cos(lat2 * degree_to_rad) * pow(math.sin(d_long / 2), 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    km = 6367 * c
    return km


  '''
  Update ctrl/home/drone markers on the map with the next set of coordinates in the table list.
  '''
  def setFrame(self):
    while self.isPlaying and self.currentRow != None:
      self.tree.see(self.currentRow)
      self.tree.selection_set(self.currentRow)
      self.setMarkers(self.currentRow)
      speed = self.selectedPlaySpeed.get() # skip frames to play faster.
      skipFrames = 1
      pause = False
      if (speed == SelectablePlaybackSpeeds.REALTIME.value):
        pause = True
      elif (speed != SelectablePlaybackSpeeds.FAST.value):
        skipFrames = int(re.sub("[^0-9]", "", speed))
      rows = self.tree.get_children()
      oldIdx = self.tree.index(self.currentRow)
      nextIdx = oldIdx + skipFrames
      if (len(rows) > nextIdx+1):
        nextRow = rows[nextIdx]
        nextFlightNum = self.tree.item(nextRow)['values'][self.columns.index('flight')]
        if nextFlightNum == 0:
          self.currentRow = None
          self.isPlaying = False
        else:
          if (pause):
            thisFrameTs = datetime.datetime.now()
            lastFrameDiff = thisFrameTs - self.lastFrameTs
            droneDiffTs = self.getDatetime(self.tree.item(nextRow)['values'][self.columns.index('timestamp')]) - self.getDatetime(self.tree.item(self.currentRow)['values'][self.columns.index('timestamp')])
            extraWaitSec = droneDiffTs.total_seconds() - lastFrameDiff.total_seconds()
            if (extraWaitSec > 0):
              if (extraWaitSec > 1):
                extraWaitSec = 1
              time.sleep(extraWaitSec)
            self.lastFrameTs = thisFrameTs
          self.currentRow = nextRow
      else:
        self.currentRow = None
        self.isPlaying = False
    self.currentRow = None
    self.lastFrameTs = None
    self.isPlaying = False


  '''
  Start flight playback.
  '''
  def play(self):
    if (self.isPlaying):
      self.isPlaying = False;
      return
    self.currentRow = None
    allRows = self.tree.get_children()
    if (len(allRows) == 0):
      return
    self.lastFrameTs = datetime.datetime.now()
    selectedRows = self.tree.selection()
    self.currentRow = allRows[0] if len(selectedRows) == 0 else selectedRows[0]
    flightNum = self.tree.item(self.currentRow)['values'][self.columns.index('flight')]
    if flightNum == 0:
      showinfo(title='Select Flight', message='Select a flight to play back.')
      return
    self.isPlaying = True;
    threading.Thread(target=self.setFrame, args=()).start()


  '''
  Stop flight playback.
  '''
  def stop(self):
    self.isPlaying = False;


  '''
  Jump to beginning of current flight, or the end of the previous one.
  '''
  def prevPath(self):
    self.isPlaying = False;
    idx = self.selectPath['values'].index(self.selectPath.get())
    for selected_item in self.tree.selection():
      currentRowIdx = self.tree.index(selected_item)
      startFlightIdx = self.flightStarts[self.selectedPath.get()]
      if currentRowIdx == startFlightIdx:
        if idx > 0:
          self.selectPath.set(self.selectPath['values'][idx-1])
          rowIdx = self.flightEnds[self.selectedPath.get()]
          gotoRow = self.tree.get_children()[rowIdx]
          self.tree.see(gotoRow)
          self.tree.selection_set(gotoRow)
          # Center the map at the drone landing position.
          item = self.tree.item(gotoRow)
          record = item['values']
          dronelat = float(record[self.columns.index('dronelat')])
          dronelon = float(record[self.columns.index('dronelon')])
          self.map_widget.set_position(dronelat, dronelon)
          self.setFlightSummary(int(re.sub(r"[^0-9]", r"", self.selectedPath.get())))
      else:
        rowIdx = self.flightStarts[self.selectedPath.get()]
        gotoRow = self.tree.get_children()[rowIdx]
        self.tree.see(gotoRow)
        self.tree.selection_set(gotoRow)
      break


  '''
  Jump to end of current flight, or the beginning of the next one.
  '''
  def nextPath(self):
    self.isPlaying = False;
    idx = self.selectPath['values'].index(self.selectPath.get())
    for selected_item in self.tree.selection():
      currentRowIdx = self.tree.index(selected_item)
      endFlightIdx = self.flightEnds[self.selectedPath.get()]
      if currentRowIdx == endFlightIdx:
        if idx < len(self.selectPath['values'])-1:
          self.selectPath.set(self.selectPath['values'][idx+1])
          self.choosePath(None)
      else:
        rowIdx = self.flightEnds[self.selectedPath.get()]
        gotoRow = self.tree.get_children()[rowIdx]
        self.tree.see(gotoRow)
        self.tree.selection_set(gotoRow)
      break


  '''
  Reset the application as it were before opening a file.
  '''
  def reset(self):
    self.title(f"Flight Data Viewer - {self.version}")
    self.ctrllabel = 'Ctrl'
    self.homelabel = 'Home'
    self.dronelabel = 'Drone'
    self.tree.delete(*self.tree.get_children())
    self.map_widget.set_zoom(self.defaultBlankMapZoom)
    self.map_widget.set_position(51.50722, -0.1275)
    if (self.flightPaths):
      for flightPath in self.flightPaths:
        flightPath.delete()
        flightPath = None
      self.flightPaths = None
    if (self.ctrlmarker):
      self.ctrlmarker.delete()
      self.ctrlmarker = None
    if (self.homemarker):
      self.homemarker.delete()
      self.homemarker = None
    if (self.dronemarker):
      self.dronemarker.delete()
      self.dronemarker = None
    self.pathCoords = None
    self.flightStarts = None
    self.flightEnds = None
    self.selectPath['values'] = ('--')
    self.selectedPath.set('--')
    self.labelFlight['text'] = ''
    if (not self.tinyScreen):
      self.labelFile['text'] = ''
    self.zipFilename = None
    self.setTableView(None)
    self.setTileSource(None)
    self.flightStats = None


  '''
  Update ctrl/home/drone markers on the map as well as other labels with flight information.
  '''
  def setMarkers(self, row):
    item = self.tree.item(row)
    record = item['values']
    # Controller Marker.
    if (self.showMarkerCtrl and self.showMarkerCtrl.get() == 'Y'):
      try:
        ctrllat = float(record[self.columns.index('ctrllat')])
        ctrllon = float(record[self.columns.index('ctrllon')])
        if (self.ctrlmarker):
          self.ctrlmarker.set_position(ctrllat, ctrllon)
        else:
          self.ctrlmarker = self.map_widget.set_marker(
            ctrllat, ctrllon, text=self.ctrllabel,
            text_color=self.markerLabelColor[int(self.markerColorSet.get())],
            marker_color_circle=self.ctrlMarkerColor1[int(self.markerColorSet.get())],
            marker_color_outside=self.ctrlMarkerColor2[int(self.markerColorSet.get())])
      except:
        self.ctrlmarker = None # Handle bad coordinates.
    else:
      if (self.ctrlmarker):
        self.ctrlmarker.delete()
        self.ctrlmarker = None
    # Drone Home (RTH) Marker.
    if (self.showMarkerHome and self.showMarkerHome.get() == 'Y'):
      try:
        homelat = float(record[self.columns.index('homelat')])
        homelon = float(record[self.columns.index('homelon')])
        if (self.homemarker):
          self.homemarker.set_position(homelat, homelon)
        else:
          self.homemarker = self.map_widget.set_marker(
            homelat, homelon, text=self.homelabel,
            text_color=self.markerLabelColor[int(self.markerColorSet.get())],
            marker_color_circle=self.homeMarkerColor1[int(self.markerColorSet.get())],
            marker_color_outside=self.homeMarkerColor2[int(self.markerColorSet.get())])
      except:
        self.homemarker = None # Handle bad coordinates.
    else:
      if (self.homemarker):
        self.homemarker.delete()
        self.homemarker = None
    # Drone marker.
    try:
      dronelat = float(record[self.columns.index('dronelat')])
      dronelon = float(record[self.columns.index('dronelon')])
      if (self.dronemarker):
        self.dronemarker.set_position(dronelat, dronelon)
      else:
        self.dronemarker = self.map_widget.set_marker(
          dronelat, dronelon, text=self.dronelabel,
          text_color=self.markerLabelColor[int(self.markerColorSet.get())],
          marker_color_circle=self.droneMarkerColor1[int(self.markerColorSet.get())],
          marker_color_outside=self.droneMarkerColor2[int(self.markerColorSet.get())])
    except:
      self.dronemarker = None # Handle bad coordinates.
    dist = record[self.columns.index('distance3')]
    alt = record[self.columns.index('altitude2')]
    Hspeed = record[self.columns.index('speed2')]
    Vspeed = record[self.columns.index('speed2vert')]
    rssi = record[self.columns.index('rssi')]
    droneconnected = 'Y' if (record[self.columns.index('flightctrlconnected')]) == 1 else 'N'
    flightTs = record[self.columns.index('time')]
    labelPad = '' if self.smallScreen else '    '
    if (self.tinyScreen):
      self.labelFlight['text'] = f'{labelPad}Dist: {dist}{self.distUnit()} / Alt: {alt}{self.distUnit()} / H Speed: {Hspeed}{self.speedUnit()} / V Speed: {Vspeed}{self.speedUnit()}'
    elif (self.smallScreen):
      self.labelFlight['text'] = f'{labelPad}Time: {flightTs} / Dist: {dist}{self.distUnit()} / Alt: {alt}{self.distUnit()} / H Speed: {Hspeed}{self.speedUnit()}  / V Speed: {Vspeed}{self.speedUnit()}'
    else:
      self.labelFlight['text'] = f'{labelPad}Time: {flightTs}   /   Distance ({self.distUnit()}): {dist}   /   Altitude ({self.distUnit()}): {alt}   /   Horiz. Speed ({self.speedUnit()}): {Hspeed}   /   Vert. Speed ({self.speedUnit()}): {Vspeed}   /   RSSI: {rssi}   /   Connected: {droneconnected}'
    pathNum = record[self.columns.index('flight')]
    if pathNum != 0:
      self.selectPath.set(f'Flight {pathNum}')
    self.setFlightSummary(pathNum)


  '''
  Return specified distance in the proper Unit (metric vs imperial).
  '''
  def distVal(self, num):
    if self.imperial.get() == 'Y':
      return num * 3.28084
    return num


  '''
  Return selected distance unit of measure.
  '''
  def distUnit(self):
    if self.imperial.get() == 'Y':
      return "ft"
    return "m"


  '''
  Return specified speed in the proper Unit (metric vs imperial).
  '''
  def speedVal(self, num):
    if self.imperial.get() == 'Y':
      return num * 2.236936
    return num


  '''
  Return selected speed unit of measure.
  '''
  def speedUnit(self):
    if self.imperial.get() == 'Y':
      return "mph"
    return "m/s"


  '''
  Format number based on selected rounding option.
  '''
  def fmtNum(self, num):
    if (num is None):
      return ''
    return f"{num:.0f}" if self.rounded.get() == 'Y' else f"{num:.2f}"


  '''
  Called when the flight summary on the screen should be updated.
  '''
  def setFlightSummary(self, pathNum):
    if (self.displayMode == "DREAMER"):
      if (not self.tinyScreen):
        if (self.smallScreen):
          self.labelFile['text'] = f'Max Dist ({self.distUnit()}): {self.flightStats[pathNum][0]:8.2f}  /  Max Alt ({self.distUnit()}): {self.flightStats[pathNum][1]:7.2f}  /  Duration: {self.flightStats[pathNum][3]}'
        else:
          self.labelFile['text'] = f'    Max Dist ({self.distUnit()}): {self.flightStats[pathNum][0]:8.2f}   /   Max Alt ({self.distUnit()}): {self.flightStats[pathNum][1]:7.2f}   /   Duration: {self.flightStats[pathNum][3]}'
    else:
      if (not self.tinyScreen):
        if (self.smallScreen):
          if self.rounded.get() == 'Y':
            self.labelFile['text'] = f'Max Dist ({self.distUnit()}): {self.flightStats[pathNum][0]:6.0f}  /  Max Alt ({self.distUnit()}): {self.flightStats[pathNum][1]:5.0f}  /  Max Speed ({self.speedUnit()}): {self.flightStats[pathNum][2]:4.0f}  /  Duration: {self.flightStats[pathNum][3]}'
          else:
            self.labelFile['text'] = f'Max Dist ({self.distUnit()}): {self.flightStats[pathNum][0]:8.2f}  /  Max Alt ({self.distUnit()}): {self.flightStats[pathNum][1]:7.2f}  /  Max Speed ({self.speedUnit()}): {self.flightStats[pathNum][2]:6.2f}  /  Duration: {self.flightStats[pathNum][3]}'
        else:
          if self.rounded.get() == 'Y':
            self.labelFile['text'] = f'    Max Dist ({self.distUnit()}): {self.flightStats[pathNum][0]:6.0f}   /   Max Alt ({self.distUnit()}): {self.flightStats[pathNum][1]:5.0f}   /   Max Speed ({self.speedUnit()}): {self.flightStats[pathNum][2]:4.0f}   /   Duration: {self.flightStats[pathNum][3]}'
          else:
            self.labelFile['text'] = f'    Max Dist ({self.distUnit()}): {self.flightStats[pathNum][0]:8.2f}   /   Max Alt ({self.distUnit()}): {self.flightStats[pathNum][1]:7.2f}   /   Max Speed ({self.speedUnit()}): {self.flightStats[pathNum][2]:6.2f}   /   Duration: {self.flightStats[pathNum][3]}'


  '''
  Called when a flight path has been selected from the dropdown.
  '''
  def choosePath(self, event):
    if (self.selectedPath.get() == '--'):
      self.setFlightSummary(0)
      return
    idx = self.flightStarts[self.selectedPath.get()]
    gotoRow = self.tree.get_children()[idx]
    self.tree.see(gotoRow)
    self.tree.selection_set(gotoRow)
    # Center the map at the drone lift-off position.
    item = self.tree.item(gotoRow)
    record = item['values']
    dronelat = float(record[self.columns.index('dronelat')])
    dronelon = float(record[self.columns.index('dronelon')])
    self.map_widget.set_position(dronelat, dronelon)
    self.setFlightSummary(int(re.sub(r"[^0-9]", r"", self.selectedPath.get())))


  '''
  Called when map needs to be redrawn, for instance when preferences change.
  '''
  def reDrawMap(self):
    self.stop()
    if (self.ctrlmarker):
      self.ctrlmarker.delete()
      self.ctrlmarker = None
    if (self.homemarker):
      self.homemarker.delete()
      self.homemarker = None
    if (self.dronemarker):
      self.dronemarker.delete()
      self.dronemarker = None
    for selected_item in self.tree.selection():
      self.setMarkers(selected_item)
      break
    if (self.showPath.get() == 'Y'):
      self.showPath.set('N')
      self.setPathView()
      self.showPath.set('Y')
      self.setPathView()


  '''
  Called when Controller Marker checkbox has been selected.
  '''
  def setMarkerCtrl(self):
    self.saveConfig()
    self.reDrawMap()


  '''
  Called when Home Marker checkbox has been selected.
  '''
  def setMarkerHome(self):
    self.saveConfig()
    self.reDrawMap()


  '''
  Called when flight path width has been changed. Redraw path if it's currently visible.
  '''
  def setPathWidth(self):
    self.saveConfig()
    self.reDrawMap()


  '''
  Called when Color Scheme selection has been changed. Redraw path if it's currently visible.
  '''
  def setMarkerColorSet(self):
    self.saveConfig()
    self.reDrawMap()


  '''
  Called when Color Scheme selection has been changed. Redraw path if it's currently visible.
  '''
  def setPathColorSet(self):
    self.saveConfig()
    self.reDrawMap()


  '''
  Called when Unit of Measure is switched between Metric/Imperial units.
  '''
  def setImperial(self):
    self.saveConfig()
    showinfo(title='App Restart Required', message='Changes will be effective next time you start the app.')


  '''
  Called when Default number of Data Rows Displayed is changed.
  '''
  def setDefaultDataRows(self):
    self.saveConfig()
    showinfo(title='App Restart Required', message='Changes will be effective next time you start the app.')


  '''
  Called when metric rounding is turned on/off.
  '''
  def setRounded(self):
    self.saveConfig()
    showinfo(title='App Restart Required', message='Changes will be effective on the next log file opened or app restart.')


  '''
  Convenience function to return the datetime from a string.
  '''
  def getDatetime(self, stringVal):
    dt = None
    try:
      dt = datetime.datetime.strptime(stringVal, '%Y-%m-%d %H:%M:%S.%f')
    except:
      dt = datetime.datetime.strptime(stringVal, '%Y-%m-%d %H:%M:%S')
    return dt


  '''
  Update markers on the map if a row in the table list has been selected.
  '''
  def item_selected(self, event):
    for selected_item in self.tree.selection():
      self.setMarkers(selected_item)
      break


  '''
  Called when Map Tile choice selection changes.
  '''
  def setTileSource(self, event):
    tileSource = self.selectedTile.get()
    if (tileSource == SelectableTileServer.GOOGLE_STANDARD.value):
      self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)  # google normal
    elif (tileSource == SelectableTileServer.GOOGLE_SATELLITE.value):
      self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)  # google satellite
    elif (tileSource == SelectableTileServer.OPEN_TOPO.value):
      self.map_widget.set_tile_server("https://tile.opentopomap.org/{z}/{x}/{y}.png")
    else:
      self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")  # OpenStreetMap (default)
    if event is not None:
      self.saveConfig()


  '''
  Called when playback speed dropdown has changed.
  '''
  def setPlaySpeed(self, event):
    if event is not None:
      self.saveConfig()


  '''
  Called when table view dropdown has changed.
  '''
  def setTableView(self, event):
    tableView = self.selectedTableView.get()
    if (tableView == SelectableMetrics.DIAGNOSTICS.value):
      self.tree['displaycolumns'] = self.columns
    elif (tableView == SelectableMetrics.ADVANCED.value):
      if (self.displayMode == "DREAMER"):
        self.tree['displaycolumns'] = self.showColsAdvDreamer
      else:
        self.tree['displaycolumns'] = self.showColsAdvAtom
    else:
      if (self.displayMode == "DREAMER"):
        self.tree['displaycolumns'] = self.showColsBasicDreamer
      else:
        self.tree['displaycolumns'] = self.showColsBasicAtom
    if event is not None:
      self.saveConfig()


  '''
  Called when checkbox for Path view is selected (to show or hide drone path on the map).
  '''
  def setPathView(self):
    if not self.pathCoords:
      return
    if (self.showPath.get() == 'Y'):
      colors = self.pathColors[int(self.pathColorSet.get())]
      self.flightPaths = []
      idx = 0
      for pathCoord in self.pathCoords:
        self.flightPaths.append(self.map_widget.set_path(width=self.pathWidth.get(), position_list=pathCoord, color=colors[idx%len(colors)]))
        idx = idx + 1
    else:
      if (self.flightPaths):
        for flightPath in self.flightPaths:
          flightPath.delete()
          flightPath = None
        self.flightPaths = None


  '''
  Save the flight data in a CSV file.
  '''
  def saveFile(self, csvFilename):
    with open(csvFilename, 'w') as f:
      head = ''
      for colref in self.tree['displaycolumns']:
        colTitle = self.tree.heading(colref)['text']
        if len(head) > 0:
          head = head + ','
        head = head + colTitle
      f.write(head)
      for rowid in self.tree.get_children():
        vals = self.tree.item(rowid)['values']
        hasWritten = False
        colIdx = 0
        f.write('\n')
        for colref in self.tree['columns']:
          if colref in self.tree['displaycolumns']:
            if (hasWritten):
              f.write(',')
            f.write('"' + str(vals[colIdx]) + '"')
            hasWritten = True
          colIdx = colIdx + 1;
    f.close()
    showinfo(title='Export Completed', message=f'Data has been exported to {csvFilename}')


  '''
  Open the selected Flight Data Zip file.
  '''
  def parseFile(self, selectedFile):
    zipFile = Path(selectedFile);
    if (not zipFile.is_file()):
      showerror(title='Invalid File', message=f'Not a valid file specified: {selectedFile}')
      return

    droneModel = re.sub(r"[0-9]*-(.*)-Drone.*", r"\1", PurePath(selectedFile).name) # Pull drone model from zip filename.
    droneModel = re.sub(r"[^\w]", r" ", droneModel) # Remove non-alphanumeric characters from the model name.
    lcDM = droneModel.lower()
    if ('p1a' in droneModel.lower()):
      self.parseDreamerLogs(droneModel, selectedFile)
    else:
      if (not 'atom' in droneModel.lower()):
        showwarning(title='Unsupported Model', message=f'This drone model may not be supported in this software: {droneModel}')
      self.parseAtomLogs(droneModel, selectedFile)


  '''
  Parse Atom based logs.
  '''
  def parseAtomLogs(self, droneModel, selectedFile):
    setctrl = True

    binLog = os.path.join(tempfile.gettempdir(), "flightdata")
    shutil.rmtree(binLog, ignore_errors=True) # Delete old temp files if they were missed before.

    with ZipFile(selectedFile, 'r') as unzip:
      unzip.extractall(path=binLog)

    self.stop()
    self.reset()
    self.displayMode = "ATOM"
    self.setTableView(None)
    self.zipFilename = selectedFile

    # First read the FPV file. The presence of this file is optional. The format of this
    # file differs slightly based on the mobile platform it was created on: Android vs iOS.
    # Example filenames:
    #   - 20230819190421-AtomSE-iosSystem-iPhone13Pro-FPV.bin
    #   - 20230826161313-Atom SE-Android-(samsung)-FPV.bin
    fpvStat = {}
    files = sorted(glob.glob(os.path.join(binLog, '**/*-FPV.bin'), recursive=True))
    for file in files:
      #self.ctrllabel = re.sub(r".*-\(?([^\)-]+)\)?-.*", r"\1", PurePath(file).name)
      with open(file, mode='rb') as fpvFile:
        while True:
          fpvRecord = fpvFile.readline().decode("utf-8")
          if not fpvRecord:
            break
          reclen = len(fpvRecord)
          if (reclen == 19):
            binval = fpvRecord[15:18].encode("ascii")
            hex1 = ('0' + hex(binval[0])[2:])[-2:]
            hex2 = ('0' + hex(binval[1])[2:])[-2:]
            hex3 = ('0' + hex(binval[2])[2:])[-2:]
            fpvStat[fpvRecord[:14]] = f'00{hex1}{hex2}{hex3}' # iOS
          elif (reclen == 24):
            fpvStat[fpvRecord[:14]] = fpvRecord[15:] # Android
      fpvFile.close()

    # Read the Flight Status files. These files are required to be present.
    files = sorted(glob.glob(os.path.join(binLog, '**/*-FC.bin'), recursive=True) + glob.glob(os.path.join(binLog, '**/*-FC.fc'), recursive=True))
    if (len(files) == 0):
      showerror(title='Empty Log File', message=f'Log file is empty: {selectedFile}')
      return

    timestampMarkers = []

    # First grab timestamps from the filenames. Those are used to calculate the real timestamps with the elapsed time from each record.
    for file in files:
      timestampMarkers.append(datetime.datetime.strptime(re.sub("-.*", "", Path(file).stem), '%Y%m%d%H%M%S'))

    filenameTs = timestampMarkers[0]
    prevReadingTs = timestampMarkers[0]
    firstTs = None
    maxDist = 0;
    maxAlt = 0;
    maxSpeed = 0;
    self.pathCoords = []
    self.flightStarts = {}
    self.flightEnds = {}
    self.flightStats = []
    pathCoord = []
    isNewPath = True
    isFlying = False
    recordCount = 0
    tableLen = 0
    for file in files:
      offset1 = 0
      offset2 = 0
      if file.endswith(".fc"):
        offset1 = -6
        offset2 = -10
      flightStat = [0, 0, 0] # Max dist, max alt, max speed
      with open(file, mode='rb') as flightFile:
        while True:
          fcRecord = flightFile.read(512)
          if (len(fcRecord) < 512):
            break

          recordCount = recordCount + 1
          recordId = struct.unpack('<I', fcRecord[0:4])[0] # This incremental record count is generated by the Potensic Pro app. All other fields are generated directly on the drone itself. The Potensic App saves these drone logs to the .bin files on the mobile device.
          elapsed = struct.unpack('<Q', fcRecord[5:13])[0] # Microseconds elapsed since previous reading.
          if (elapsed == 0):
            continue # handle rare case of invalid record
          satellites = struct.unpack('<B', fcRecord[46:47])[0] # Number of satellites.
          dronelat = struct.unpack('<i', fcRecord[53+offset1:57+offset1])[0]/10000000 # Drone coords.
          dronelon = struct.unpack('<i', fcRecord[57+offset1:61+offset1])[0]/10000000
          ctrllat = struct.unpack('<i', fcRecord[159+offset2:163+offset2])[0]/10000000 # Controller coords.
          ctrllon = struct.unpack('<i', fcRecord[163+offset2:167+offset2])[0]/10000000
          homelat = struct.unpack('<i', fcRecord[435+offset2:439+offset2])[0]/10000000 # Home Point coords (for Return To Home).
          homelon = struct.unpack('<i', fcRecord[439+offset2:443+offset2])[0]/10000000
          dist1lat = self.distVal(struct.unpack('f', fcRecord[235+offset2:239+offset2])[0]) # Distance home point vs controller??
          dist1lon = self.distVal(struct.unpack('f', fcRecord[239+offset2:243+offset2])[0])
          dist2lat = self.distVal(struct.unpack('f', fcRecord[319+offset2:323+offset2])[0]) # Distance home point vs controller??
          dist2lon = self.distVal(struct.unpack('f', fcRecord[323+offset2:327+offset2])[0])
          dist1 = round(math.sqrt(math.pow(dist1lat, 2) + math.pow(dist1lon, 2)), 2) # Pythagoras to calculate real distance.
          dist2 = round(math.sqrt(math.pow(dist2lat, 2) + math.pow(dist2lon, 2)), 2) # Pythagoras to calculate real distance.
          dist3 = self.distVal(struct.unpack('f', fcRecord[431+offset2:435+offset2])[0]) # Distance from home point, as reported by the drone.
          gps = struct.unpack('f', fcRecord[279+offset2:283+offset2])[0] # GPS (-1 = no GPS, 0 = GPS ready, 2 and up = GPS in use)
          gpsStatus = 'Yes' if gps >= 0 else 'No'
          #sdff = (special - 2) * 4 * 60 * 1000
          #elms = 0 if sdff < 0 else datetime.timedelta(milliseconds=sdff) # possibly elapsed flight time??
          #flightCount = struct.unpack('<B', fcRecord[303+offset2:304+offset2])[0] # Some sort of counter.
          #spec4 = struct.unpack('<B', fcRecord[304+offset2:305+offset2])[0] # ?
          #spec5 = struct.unpack('<B', fcRecord[305+offset2:306+offset2])[0] # ?
          #spec6 = struct.unpack('<B', fcRecord[306+offset2:307+offset2])[0] # ?
          #spec7 = struct.unpack('<B', fcRecord[307+offset2:308+offset2])[0] # ?
          motor1Stat = struct.unpack('<B', fcRecord[312+offset2:313+offset2])[0] # Motor 1 speed (3 = off, 4 = idle, 5 = low, 6 = medium, 7 = high)
          motor2Stat = struct.unpack('<B', fcRecord[314+offset2:315+offset2])[0] # Motor 2 speed (3 = off, 4 = idle, 5 = low, 6 = medium, 7 = high)
          motor3Stat = struct.unpack('<B', fcRecord[316+offset2:317+offset2])[0] # Motor 3 speed (3 = off, 4 = idle, 5 = low, 6 = medium, 7 = high)
          motor4Stat = struct.unpack('<B', fcRecord[318+offset2:319+offset2])[0] # Motor 4 speed (3 = off, 4 = idle, 5 = low, 6 = medium, 7 = high)
          droneInUse = struct.unpack('<B', fcRecord[295+offset2:296+offset2])[0] # Drone is detected "in action" (0 = flying or in use, 1 = not in use).
          inUse = 'Yes' if droneInUse == 0 else 'No'

          if (dist3 > maxDist):
            maxDist = dist3
          alt1 = round(self.distVal(-struct.unpack('f', fcRecord[243+offset2:247+offset2])[0]), 2) # Relative height from controller vs distance to ground??
          alt2 = round(self.distVal(-struct.unpack('f', fcRecord[343+offset2:347+offset2])[0]), 2) # Relative height from controller vs distance to ground??
          if (alt2 > maxAlt):
            maxAlt = alt2
          speed1lat = self.speedVal(struct.unpack('f', fcRecord[247+offset2:251+offset2])[0])
          speed1lon = self.speedVal(struct.unpack('f', fcRecord[251+offset2:255+offset2])[0])
          speed2lat = self.speedVal(struct.unpack('f', fcRecord[327+offset2:331+offset2])[0])
          speed2lon = self.speedVal(struct.unpack('f', fcRecord[331+offset2:335+offset2])[0])
          speed1 = round(math.sqrt(math.pow(speed1lat, 2) + math.pow(speed1lon, 2)), 2) # Pythagoras to calculate real speed.
          speed2 = round(math.sqrt(math.pow(speed2lat, 2) + math.pow(speed2lon, 2)), 2) # Pythagoras to calculate real speed.
          if (speed2 > maxSpeed):
            maxSpeed = speed2
          speed1vert = self.speedVal(-struct.unpack('f', fcRecord[255+offset2:259+offset2])[0])
          speed2vert = self.speedVal(-struct.unpack('f', fcRecord[347+offset2:351+offset2])[0])

          # Some checks to handle cases with bad or incomplete GPS data.
          hasDroneCoords = dronelat != 0.0 and dronelon != 0.0
          hasCtrlCoords = ctrllat != 0.0 and ctrllon != 0.0
          hasHomeCoords = homelat != 0.0 and homelon != 0.0
          sanDist = 0
          if (hasDroneCoords and hasHomeCoords):
            try:
              sanDist = self.haversine(homelat, homelon, dronelat, dronelon)
            except:
              sanDist = 9999
          elif (hasDroneCoords and hasCtrlCoords):
            try:
              sanDist = self.haversine(ctrllat, ctrllon, dronelat, dronelon)
            except:
              sanDist = 9999

          hasValidCoords = sanDist < 20 and hasDroneCoords and (hasCtrlCoords or hasHomeCoords)

          droneMotorStatus = MotorStatus.UNKNOWN
          if motor1Stat > 4 or motor2Stat > 4 or motor3Stat > 4 or motor4Stat > 4:
            droneMotorStatus = MotorStatus.LIFT
          elif motor1Stat == 4 or motor2Stat == 4 or motor3Stat == 4 or motor4Stat == 4:
            droneMotorStatus = MotorStatus.IDLE
          elif motor1Stat == 3 and motor2Stat == 3 and motor3Stat == 3 and motor4Stat == 3:
            droneMotorStatus = MotorStatus.OFF
          statusChanged = False
          if isFlying:
            if droneMotorStatus == MotorStatus.OFF:
              isFlying = False
              statusChanged = True
              firstTs = None
          elif droneMotorStatus == MotorStatus.LIFT:
            isFlying = True
            statusChanged = True
          else:
            firstTs = None

          # Calculate timestamp for the record.
          readingTs = filenameTs + datetime.timedelta(milliseconds=(elapsed/1000))
          while (readingTs < prevReadingTs):
            # Line up to the next valid timestamp marker (pulled from the filenames).
            try:
              filenameTs = timestampMarkers.pop(0)
              readingTs = filenameTs + datetime.timedelta(milliseconds=(elapsed/1000))
            except:
              # Handle rare case where log files contain mismatched "elapsed" indicators and times in bin filenames.
              readingTs = prevReadingTs

          # Calculate elapsed time for the flight.
          if firstTs is None:
            firstTs = readingTs
          elapsedTs = readingTs - firstTs
          elapsedTs = elapsedTs - datetime.timedelta(microseconds=elapsedTs.microseconds)
          prevReadingTs = readingTs

          # Build paths for each flight and keep metric summaries of each path (flight), as well as for the entire log file.
          pathNum = 0
          if pathNum == len(self.flightStats):
            self.flightStats.append([dist3, alt2, speed2, None])
          else:
            if dist3 > self.flightStats[pathNum][0]:
              self.flightStats[pathNum][0] = dist3
            if alt2 > self.flightStats[pathNum][1]:
              self.flightStats[pathNum][1] = alt2
            if speed2 > self.flightStats[pathNum][2]:
              self.flightStats[pathNum][2] = speed2
          if (hasValidCoords):
            if (statusChanged): # start new flight path if current one ends or new one begins.
              if (len(pathCoord) > 0):
                self.pathCoords.append(pathCoord)
                pathCoord = []
                isNewPath = True
            if (isFlying): # Only trace path when the drone's motors are spinning faster than idle speeds.
              pathNum = len(self.pathCoords)+1
              pathCoord.append((dronelat, dronelon))
              if pathNum == len(self.flightStats):
                self.flightStats.append([dist3, alt2, speed2, elapsedTs])
              else:
                if dist3 > self.flightStats[pathNum][0]:
                  self.flightStats[pathNum][0] = dist3
                if alt2 > self.flightStats[pathNum][1]:
                  self.flightStats[pathNum][1] = alt2
                if speed2 > self.flightStats[pathNum][2]:
                  self.flightStats[pathNum][2] = speed2
                self.flightStats[pathNum][3] = elapsedTs

          # Get corresponding record from the controller. There may not be one, or any at all. Match up to 5 seconds ago.
          fpvRssi = ""
          fpvChannel = ""
          #fpvWirelessConnected = ""
          fpvFlightCtrlConnected = ""
          fpvRemoteConnected = ""
          #fpvHighDbm = ""
          fpvRecord = fpvStat.get(readingTs.strftime('%Y%m%d%H%M%S'));
          secondsAgo = -1;
          while (not fpvRecord):
            fpvRecord = fpvStat.get((readingTs + datetime.timedelta(seconds=secondsAgo)).strftime('%Y%m%d%H%M%S'));
            if (secondsAgo <= -5):
              break;
            secondsAgo = secondsAgo - 1;
          if (fpvRecord):
            fpvRssi = str(int(fpvRecord[2:4], 16))
            fpvChannel = str(int(fpvRecord[4:6], 16))
            fpvFlags = int(fpvRecord[6:8], 16)
            #fpvWirelessConnected = "1" if fpvFlags & 1 == 1 else "0"
            fpvFlightCtrlConnected = "1" if fpvFlags & 2 == 2 else "0" # Drone to controller connection.
            fpvRemoteConnected = "1" if fpvFlags & 4 == 4 else "0"
            #fpvHighDbm = "1" if fpvFlags & 32 == 32 else "0"

          if (isNewPath and len(pathCoord) > 0):
            self.flightStarts[f'Flight {pathNum}'] = tableLen
            isNewPath = False
          if pathNum > 0:
            self.flightEnds[f'Flight {pathNum}'] = tableLen
          self.tree.insert('', tk.END, value=(recordCount, recordId, pathNum, readingTs.isoformat(sep=' '), readingTs.strftime('%X'), elapsedTs, droneMotorStatus.value, f"{self.fmtNum(dist1)}", f"{self.fmtNum(dist1lat)}", f"{self.fmtNum(dist1lon)}", f"{self.fmtNum(dist2)}", f"{self.fmtNum(dist2lat)}", f"{self.fmtNum(dist2lon)}", f"{self.fmtNum(dist3)}", f"{self.fmtNum(alt1)}", f"{self.fmtNum(alt2)}", f"{self.fmtNum(speed1)}", f"{self.fmtNum(speed1lat)}", f"{self.fmtNum(speed1lon)}", f"{self.fmtNum(speed2)}", f"{self.fmtNum(speed2lat)}", f"{self.fmtNum(speed2lon)}", f"{self.fmtNum(speed1vert)}", f"{self.fmtNum(speed2vert)}", str(satellites), str(ctrllat), str(ctrllon), str(homelat), str(homelon), str(dronelat), str(dronelon), fpvRssi, fpvChannel, fpvFlightCtrlConnected, fpvRemoteConnected, gpsStatus, inUse, motor1Stat, motor2Stat, motor3Stat, motor4Stat))
          tableLen = tableLen + 1
          if (setctrl and hasValidCoords and alt2 > 0): # Record home location from the moment the drone ascends.
            #self.dronelabel = droneModel
            self.map_widget.set_zoom(self.defaultDroneZoom)
            self.map_widget.set_position(dronelat, dronelon)
            self.ctrlmarker = self.map_widget.set_marker(
              ctrllat, ctrllon, text=self.ctrllabel,
              text_color=self.markerLabelColor[int(self.markerColorSet.get())],
              marker_color_circle=self.ctrlMarkerColor1[int(self.markerColorSet.get())],
              marker_color_outside=self.ctrlMarkerColor2[int(self.markerColorSet.get())])
            setctrl = False

      flightFile.close()

    shutil.rmtree(binLog, ignore_errors=True) # Delete temp files.

    self.title(f"Flight Data Viewer - {self.version} - {PurePath(selectedFile).name}")
    if (len(pathCoord) > 0):
      self.pathCoords.append(pathCoord)
    self.setPathView()
    pathNames = list(self.flightStarts.keys())
    if (len(pathNames) > 0):
      self.selectPath['values'] = pathNames
      self.selectedPath.set(pathNames[0])
    self.choosePath(None)
    for i in range(1, len(self.flightStats)):
      if self.flightStats[0][3] == None:
        self.flightStats[0][3] = self.flightStats[i][3]
      else:
        self.flightStats[0][3] = self.flightStats[0][3] + self.flightStats[i][3]



  '''
  Parse Dreamer based logs.
  '''
  def parseDreamerLogs(self, droneModel, selectedFile):
    setctrl = True

    binLog = os.path.join(tempfile.gettempdir(), "flightdata")
    shutil.rmtree(binLog, ignore_errors=True) # Delete old temp files if they were missed before.

    with ZipFile(selectedFile, 'r') as unzip:
      unzip.extractall(path=binLog)

    self.stop()
    self.reset()
    self.displayMode = "DREAMER"
    self.setTableView(None)
    self.zipFilename = selectedFile

    # First read the FPV file. The presence of this file is optional.
    fpvStat = {}
    files = sorted(glob.glob(os.path.join(binLog, '**/*-FPV.bin'), recursive=True))
    for file in files:
      #self.ctrllabel = re.sub(r".*-\(?([^\)-]+)\)?-.*", r"\1", PurePath(file).name)
      with open(file, mode='rb') as fpvFile:
        while True:
          fpvRecord = fpvFile.readline().decode("utf-8")
          if not fpvRecord:
            break
          reclen = len(fpvRecord)
          if (reclen == 19):
            binval = fpvRecord[15:18].encode("ascii")
            hex1 = ('0' + hex(binval[0])[2:])[-2:]
            hex2 = ('0' + hex(binval[1])[2:])[-2:]
            hex3 = ('0' + hex(binval[2])[2:])[-2:]
            fpvStat[fpvRecord[:14]] = f'00{hex1}{hex2}{hex3}' # iOS
          elif (reclen == 24):
            fpvStat[fpvRecord[:14]] = fpvRecord[15:] # Android
      fpvFile.close()

    # Read the Flight Status files. These files are required to be present.
    files = sorted(glob.glob(os.path.join(binLog, '**/*-FC.bin'), recursive=True))
    timestampMarkers = []

    # First grab timestamps from the filenames. Those are used to calculate the real timestamps with the elapsed time from each record.
    for file in files:
      timestampMarkers.append(datetime.datetime.strptime(re.sub("-.*", "", Path(file).stem), '%Y%m%d%H%M%S'))

    filenameTs = timestampMarkers[0]
    prevReadingTs = timestampMarkers[0]
    readingTs = timestampMarkers[0]
    firstTs = None
    maxDist = 0;
    maxAlt = 0;
    maxSpeed = 0;
    self.pathCoords = []
    self.flightStarts = {}
    self.flightEnds = {}
    self.flightStats = []
    pathCoord = []
    isNewPath = True
    isFlying = False
    recordCount = 0
    tableLen = 0
    for file in files:
      with open(file, mode='rb') as flightFile:
        while True:
          fcRecord = flightFile.read(512)
          if (len(fcRecord) < 512):
            break

          recordCount = recordCount + 1
          recordId = struct.unpack('<I', fcRecord[0:4])[0] # 4 bytes.
          elapsed = struct.unpack('<I', fcRecord[33:37])[0]
          if (elapsed == 0):
            continue # handle rare case of invalid record
          satellites = struct.unpack('<B', fcRecord[7:8])[0]
          dronelon = struct.unpack('f', fcRecord[145:149])[0]
          dronelat = struct.unpack('f', fcRecord[149:153])[0]
          alt1 = self.distVal(struct.unpack('<h', fcRecord[39:41])[0] / 10)
          alt2 = self.distVal(struct.unpack('<h', fcRecord[59:61])[0] / 10)
          dist1lat = self.distVal(struct.unpack('<h', fcRecord[37:39])[0] / 10)
          dist1lon = self.distVal(struct.unpack('<h', fcRecord[41:43])[0] / 10)
          dist2lat = self.distVal(struct.unpack('<h', fcRecord[57:59])[0] / 10)
          dist2lon = self.distVal(struct.unpack('<h', fcRecord[61:63])[0] / 10)
          dist1 = round(math.sqrt(math.pow(dist1lat, 2) + math.pow(dist1lon, 2)), 2) # Pythagoras to calculate real distance.
          dist2 = round(math.sqrt(math.pow(dist2lat, 2) + math.pow(dist2lon, 2)), 2) # Pythagoras to calculate real distance.
          earth_radius_in_km = 6367 # 6378.137
          coeff = (1 / ((2 * math.pi / 360) * earth_radius_in_km)) / 1000
          real1lat = dronelat + ((dist1lat) * coeff)
          real1lon = dronelon + (((dist1lon) * coeff) / (math.cos(dronelat * math.pi / 180)))
          #real1lon = dronelon + (((dist1lon) * coeff) / (math.cos(dronelat * 0.018)))

          hasValidCoords = dronelat != 0.0 and dronelon != 0.0

          statusChanged = False
          if isFlying:
            if dist1 == 0 and alt1 == 0:
              isFlying = False
              statusChanged = True
              firstTs = None
          elif alt1 > 0:
            isFlying = True
            statusChanged = True
          else:
            firstTs = None

          # Calculate timestamp for the record.
          readingTs = readingTs + datetime.timedelta(milliseconds=(elapsed/1000000))
          while (readingTs < prevReadingTs):
            # Line up to the next valid timestamp marker (pulled from the filenames).
            filenameTs = timestampMarkers.pop(0)
            readingTs = filenameTs + datetime.timedelta(milliseconds=(elapsed/1000000))

          # Calculate elapsed time for the flight. TODO - should reset for each flight.
          if firstTs is None:
            firstTs = readingTs
          elapsedTs = readingTs - firstTs
          elapsedTs = elapsedTs - datetime.timedelta(microseconds=elapsedTs.microseconds)
          prevReadingTs = readingTs

          # Build paths for each flight. TODO - improve this logic as it's based on limited metrics, not on drone status flags.
          pathNum = 0
          if pathNum == len(self.flightStats):
            self.flightStats.append([dist1, alt1, None, None])
          else:
            if dist1 > self.flightStats[pathNum][0]:
              self.flightStats[pathNum][0] = dist1
            if alt1 > self.flightStats[pathNum][1]:
              self.flightStats[pathNum][1] = alt1
          if (hasValidCoords):
            if (statusChanged): # start new flight path if current one ends or new one begins.
              if (len(pathCoord) > 0):
                self.pathCoords.append(pathCoord)
                pathCoord = []
                isNewPath = True
            if (isFlying): # Only trace path where the drone is off the ground.
              pathNum = len(self.pathCoords)+1
              pathCoord.append((real1lat, real1lon))
              if pathNum == len(self.flightStats):
                self.flightStats.append([dist1, alt1, None, elapsedTs])
              else:
                if dist1 > self.flightStats[pathNum][0]:
                  self.flightStats[pathNum][0] = dist1
                if alt1 > self.flightStats[pathNum][1]:
                  self.flightStats[pathNum][1] = alt1
                self.flightStats[pathNum][3] = elapsedTs

          # Get corresponding record from the controller. There may not be one, or any at all. Match up to 5 seconds ago.
          fpvRssi = ""
          fpvChannel = ""
          #fpvWirelessConnected = ""
          fpvFlightCtrlConnected = ""
          fpvRemoteConnected = ""
          #fpvHighDbm = ""
          fpvRecord = fpvStat.get(readingTs.strftime('%Y%m%d%H%M%S'));
          secondsAgo = -1;
          while (not fpvRecord):
            fpvRecord = fpvStat.get((readingTs + datetime.timedelta(seconds=secondsAgo)).strftime('%Y%m%d%H%M%S'));
            if (secondsAgo <= -5):
              break;
            secondsAgo = secondsAgo - 1;
          if (fpvRecord):
            fpvRssi = str(int(fpvRecord[2:4], 16))
            fpvChannel = str(int(fpvRecord[4:6], 16))
            fpvFlags = int(fpvRecord[6:8], 16)
            #fpvWirelessConnected = "1" if fpvFlags & 1 == 1 else "0"
            fpvFlightCtrlConnected = "1" if fpvFlags & 2 == 2 else "0" # Drone to controller connection.
            fpvRemoteConnected = "1" if fpvFlags & 4 == 4 else "0"
            #fpvHighDbm = "1" if fpvFlags & 32 == 32 else "0"

          if (isNewPath and len(pathCoord) > 0):
            self.flightStarts[f'Flight {pathNum}'] = tableLen
            isNewPath = False
          if pathNum > 0:
            self.flightEnds[f'Flight {pathNum}'] = tableLen
          self.tree.insert('', tk.END, value=(recordCount, recordId, pathNum, readingTs.isoformat(sep=' '), readingTs.strftime('%X'), elapsedTs, "", f"{self.fmtNum(dist1)}", f"{self.fmtNum(dist1lat)}", f"{self.fmtNum(dist1lon)}", f"{self.fmtNum(dist2)}", f"{self.fmtNum(dist2lat)}", f"{self.fmtNum(dist2lon)}", "", f"{self.fmtNum(alt1)}", f"{self.fmtNum(alt2)}", "", "", "", "", "", "", "", "", str(satellites), "", "", str(dronelat), str(dronelon), str(real1lat), str(real1lon), "", "", "", "", "", "", "", "", ""))
          tableLen = tableLen + 1
          if (setctrl and hasValidCoords and alt1 > 0): # Record home location from the moment the drone ascends.
            #self.dronelabel = droneModel
            self.map_widget.set_zoom(self.defaultDroneZoom)
            self.map_widget.set_position(real1lat, real1lon)
            self.ctrlmarker = self.map_widget.set_marker(
              dronelat, dronelon, text=self.ctrllabel,
              text_color=self.markerLabelColor[int(self.markerColorSet.get())],
              marker_color_circle=self.ctrlMarkerColor1[int(self.markerColorSet.get())],
              marker_color_outside=self.ctrlMarkerColor2[int(self.markerColorSet.get())])
            setctrl = False

      flightFile.close()

    shutil.rmtree(binLog, ignore_errors=True) # Delete temp files.

    if (len(pathCoord) > 0):
      self.pathCoords.append(pathCoord)
    self.setPathView()
    pathNames = list(self.flightStarts.keys())
    if (len(pathNames) > 0):
      self.selectPath['values'] = pathNames
      self.selectedPath.set(pathNames[0])
    self.choosePath(None)



  '''
  File Dialog to ask for the Flight Data Zip file.
  '''
  def askForFlightFile(self):
    selectedZipfile = filedialog.askopenfilename(title='Open Flight File',filetypes=(('zip files', '*.zip'),('All files', '*.*')))
    self.parseFile(selectedZipfile)


  '''
  File Dialog to ask where to save the flight data to.
  '''
  def askForExportFile(self):
    if (self.zipFilename != None):
      selectedExportfile = filedialog.asksaveasfilename(title='Export Flight Data',filetypes=(('CSV files', '*.csv'),('All files', '*.*')))
      self.saveFile(selectedExportfile)
    else:
      showwarning(title='Nothing to Export', message='There is nothing to Export. Please open a Flight Data file first (.zip file).')


  '''
  Export file based on zip filename.
  '''
  def exportFlightFile(self):
    if (self.zipFilename != None):
      ext = "-" + self.selectedTableView.get() + ".csv"
      self.saveFile(re.sub("\.zip$", "", self.zipFilename) + ext)
    else:
      showwarning(title='Nothing to Export', message='There is nothing to Export. Please open a Flight Data file first (.zip file).')


  '''
  Gracefully clean up before exiting.
  '''
  def exitApp(self):
    self.stop()
    while (self.isPlaying):
      time.sleep(0.5)
    self.destroy()


  '''
  Return desired widget width based on device screen width.
  '''
  def scaledWidth(self, target_width):
    return int(round(target_width * self.scale))


  '''
  Return desired widget height based on device screen height.
  '''
  def scaledHeight(self, target_height):
    return int(round(target_height * self.scale))


  '''
  Read configs from storage.
  '''
  def readConfig(self):
    self.configParser = configparser.ConfigParser(allow_no_value=True)
    self.configParser.read(self.configPath)
    if ('Common' in self.configParser):
      comCfg = self.configParser['Common']
      self.pathWidth.set(comCfg['PathWidth'] if 'PathWidth' in comCfg else 1)
      self.markerColorSet.set(comCfg['MarkerColorScheme'] if 'MarkerColorScheme' in comCfg else 0)
      self.pathColorSet.set(comCfg['PathColorScheme'] if 'PathColorScheme' in comCfg else 0)
      self.imperial.set(comCfg['Imperial'] if 'Imperial' in comCfg else 'N')
      self.rounded.set(comCfg['RoundedMetrics'] if 'RoundedMetrics' in comCfg else 'Y')
      self.defaultDataRows.set(comCfg['DefaultDataRows'] if 'DefaultDataRows' in comCfg else 4)
      self.selectedPlaySpeed.set(comCfg['SelectedPlaySpeed'] if 'SelectedPlaySpeed' in comCfg else SelectablePlaybackSpeeds.FAST.value)
      self.selectedTile.set(comCfg['SelectedTileServer'] if 'SelectedTileServer' in comCfg else SelectableTileServer.OPENSTREETMAP.value)
      self.selectedTableView.set(comCfg['SelectedTableView'] if 'SelectedTableView' in comCfg else SelectableMetrics.BASIC.value)
      self.showMarkerCtrl.set(comCfg['ShowControllerMarker'] if 'ShowControllerMarker' in comCfg else 'Y')
      self.showMarkerHome.set(comCfg['ShowHomeMarker'] if 'ShowHomeMarker' in comCfg else 'N')
    else:
      self.pathWidth.set(1)
      self.markerColorSet.set(0)
      self.pathColorSet.set(0)
      self.imperial.set('N')
      self.defaultDataRows.set(4)
      self.rounded.set('Y')
      self.selectedPlaySpeed.set(SelectablePlaybackSpeeds.FAST.value)
      self.selectedTile.set(SelectableTileServer.OPENSTREETMAP.value)
      self.selectedTableView.set(SelectableMetrics.BASIC.value)
      self.showMarkerCtrl.set('Y')
      self.showMarkerHome.set('N')
      self.saveConfig()


  '''
  Save configs to storage.
  '''
  def saveConfig(self):
    self.configParser['Common'] = {
      'PathWidth': self.pathWidth.get(),
      'MarkerColorScheme': self.markerColorSet.get(),
      'PathColorScheme': self.pathColorSet.get(),
      'Imperial': self.imperial.get(),
      'RoundedMetrics': self.rounded.get(),
      'DefaultDataRows': self.defaultDataRows.get(),
      'SelectedPlaySpeed': self.selectedPlaySpeed.get(),
      'SelectedTileServer': self.selectedTile.get(),
      'SelectedTableView': self.selectedTableView.get(),
      'ShowControllerMarker': self.showMarkerCtrl.get(),
      'ShowHomeMarker': self.showMarkerHome.get()
    }
    with open(self.configPath, 'w') as cfile:
      self.configParser.write(cfile)


  '''
  Initialize.
  '''
  def __init__(self):
    super().__init__()
    charWidth = nametofont("TkDefaultFont").measure('W') # Use size of default character as way to measure how much space is on the device screen.
    self.scale = charWidth / self.defaultFontsize
    self.cpl = self.winfo_screenwidth() / charWidth # Characters per line using default font size
    self.smallScreen = self.cpl < 100
    self.tinyScreen = self.cpl < 40

    # Scale widgets based on device.
    fontFamily = 'Helvetica'
    fontSize = self.scaledWidth(14)
    nametofont("TkMenuFont").configure(family=fontFamily, size=-fontSize)
    nametofont("TkDefaultFont").configure(family=fontFamily, size=-fontSize)
    nametofont("TkHeadingFont").configure(family=fontFamily, size=-fontSize)
    nametofont("TkTextFont").configure(family=fontFamily, size=-fontSize)
    colWidth1 = self.scaledWidth(200)
    colWidth2 = self.scaledWidth(120)
    colWidth3 = self.scaledWidth(90)
    colWidth4 = self.scaledWidth(120)
    colWidth5 = self.scaledWidth(50)

    self.title(f"Flight Data Viewer - {self.version}")
    self.protocol("WM_DELETE_WINDOW", self.exitApp)
    try:
      self.wm_attributes('-zoomed', 1)
    except:
      self.state('zoomed')
    self.resizable(True, True)

    style = ttk.Style(self)
    style.theme_use('classic')

    self.pathWidth = tk.StringVar()
    self.imperial = tk.StringVar()
    self.rounded = tk.StringVar()
    self.markerColorSet = tk.StringVar()
    self.pathColorSet = tk.StringVar()
    self.defaultDataRows = tk.StringVar()
    self.selectedPlaySpeed = tk.StringVar()
    self.selectedTile = tk.StringVar()
    self.selectedTableView = tk.StringVar()
    self.showMarkerCtrl = tk.StringVar()
    self.showMarkerHome = tk.StringVar()
    self.userPath = user_data_dir("Flight Data Viewer", "extractFlightData")
    Path(self.userPath).mkdir(parents=True, exist_ok=True)
    self.configPath = os.path.join(self.userPath, self.configFilename)
    self.readConfig()

    pw = ttk.PanedWindow(orient=tk.VERTICAL)

    dataFrame = ttk.Frame(self, height=self.scaledHeight(200))
    dataFrame.columnconfigure(0, weight=1)
    dataFrame.rowconfigure(0, weight=1)

    mapFrame = ttk.Frame(self, height=self.scaledHeight(400))

    pw.add(dataFrame)
    pw.add(mapFrame)
    pw.pack(fill=tk.BOTH, expand=True)

    menubar = Menu(self)
    self.config(menu=menubar)
    file_menu = Menu(menubar, tearoff=False)

    pref_menu = Menu(file_menu, tearoff=0)
    pref_menu.add_radiobutton(label='Flight Path Width: 1', command=self.setPathWidth, variable=self.pathWidth, value=1)
    pref_menu.add_radiobutton(label='Flight Path Width: 2', command=self.setPathWidth, variable=self.pathWidth, value=2)
    pref_menu.add_radiobutton(label='Flight Path Width: 3', command=self.setPathWidth, variable=self.pathWidth, value=3)
    pref_menu.add_radiobutton(label='Flight Path Width: 4', command=self.setPathWidth, variable=self.pathWidth, value=4)
    pref_menu.add_radiobutton(label='Flight Path Width: 5', command=self.setPathWidth, variable=self.pathWidth, value=5)
    pref_menu.add_separator()
    pref_menu.add_checkbutton(label='Imperial Units', command=self.setImperial, variable=self.imperial, onvalue='Y', offvalue='N')
    pref_menu.add_checkbutton(label='Rounded Metrics', command=self.setRounded, variable=self.rounded, onvalue='Y', offvalue='N')
    pref_menu.add_separator()
    pref_menu.add_radiobutton(label='Marker Colour Scheme 1', command=self.setMarkerColorSet, variable=self.markerColorSet, value=0)
    pref_menu.add_radiobutton(label='Marker Colour Scheme 2', command=self.setMarkerColorSet, variable=self.markerColorSet, value=1)
    pref_menu.add_radiobutton(label='Marker Colour Scheme 3', command=self.setMarkerColorSet, variable=self.markerColorSet, value=2)
    pref_menu.add_radiobutton(label='Marker Colour Scheme 4', command=self.setMarkerColorSet, variable=self.markerColorSet, value=3)
    pref_menu.add_separator()
    pref_menu.add_radiobutton(label='Path Colour Scheme 1', command=self.setPathColorSet, variable=self.pathColorSet, value=0)
    pref_menu.add_radiobutton(label='Path Colour Scheme 2', command=self.setPathColorSet, variable=self.pathColorSet, value=1)
    pref_menu.add_radiobutton(label='Path Colour Scheme 3', command=self.setPathColorSet, variable=self.pathColorSet, value=2)
    pref_menu.add_radiobutton(label='Path Colour Scheme 4', command=self.setPathColorSet, variable=self.pathColorSet, value=3)
    pref_menu.add_radiobutton(label='Path Colour Scheme 5', command=self.setPathColorSet, variable=self.pathColorSet, value=4)
    pref_menu.add_radiobutton(label='Path Colour Scheme 6', command=self.setPathColorSet, variable=self.pathColorSet, value=5)
    pref_menu.add_radiobutton(label='Path Colour Scheme 7', command=self.setPathColorSet, variable=self.pathColorSet, value=6)
    pref_menu.add_radiobutton(label='Path Colour Scheme 8', command=self.setPathColorSet, variable=self.pathColorSet, value=7)
    pref_menu.add_radiobutton(label='Path Colour Scheme 9', command=self.setPathColorSet, variable=self.pathColorSet, value=8)
    pref_menu.add_separator()
    pref_menu.add_radiobutton(label='Rows Displayed: 1', command=self.setDefaultDataRows, variable=self.defaultDataRows, value=1)
    pref_menu.add_radiobutton(label='Rows Displayed: 2', command=self.setDefaultDataRows, variable=self.defaultDataRows, value=2)
    pref_menu.add_radiobutton(label='Rows Displayed: 4', command=self.setDefaultDataRows, variable=self.defaultDataRows, value=4)
    pref_menu.add_radiobutton(label='Rows Displayed: 8', command=self.setDefaultDataRows, variable=self.defaultDataRows, value=8)

    file_menu.add_command(label='Open...', command=self.askForFlightFile)
    file_menu.add_separator()
    file_menu.add_command(label='Export', command=self.exportFlightFile)
    file_menu.add_command(label='Export As...', command=self.askForExportFile)
    file_menu.add_separator()
    file_menu.add_cascade(label='Preferences', menu=pref_menu)
    file_menu.add_separator()
    file_menu.add_command(label='Close', command=self.reset)
    file_menu.add_separator()
    file_menu.add_command(label='Exit', command=self.exitApp)
    menubar.add_cascade(label='File', menu=file_menu)

    style.configure("Treeview", rowheight=int(round(charWidth * 1.75)))
    self.tree = ttk.Treeview(dataFrame, columns=self.columns, show='headings', selectmode='browse', displaycolumns=self.showColsBasicAtom, height=self.defaultDataRows.get())
    self.tree.column("recnum", anchor=tk.W, stretch=tk.NO, width=colWidth5)
    self.tree.heading('recnum', text='Rec #')
    self.tree.column("recid", anchor=tk.W, stretch=tk.NO, width=colWidth5)
    self.tree.heading('recid', text='Row Id')
    self.tree.column("flight", anchor=tk.W, stretch=tk.NO, width=colWidth5)
    self.tree.heading('flight', text='Flight')
    self.tree.column("timestamp", anchor=tk.W, stretch=tk.NO, width=colWidth1)
    self.tree.heading('timestamp', text='Timestamp (ISO)')
    self.tree.column("tod", anchor=tk.W, stretch=tk.NO, width=colWidth3)
    self.tree.heading('tod', text='Time')
    self.tree.column("time", anchor=tk.W, stretch=tk.NO, width=colWidth3)
    self.tree.heading('time', text='Flight')
    self.tree.column("flightstatus", anchor=tk.W, stretch=tk.NO, width=colWidth3)
    self.tree.heading('flightstatus', text='Motor')
    self.tree.column("distance1", anchor=tk.E, stretch=tk.NO, width=colWidth3)
    self.tree.heading('distance1', text=f'Dist1 ({self.distUnit()})')
    self.tree.column("dist1lat", anchor=tk.E, stretch=tk.NO, width=colWidth3)
    self.tree.heading('dist1lat', text=f'Lat Dist1 ({self.distUnit()})')
    self.tree.column("dist1lon", anchor=tk.E, stretch=tk.NO, width=colWidth3)
    self.tree.heading('dist1lon', text=f'Lon Dist1 ({self.distUnit()})')
    self.tree.column("distance2", anchor=tk.E, stretch=tk.NO, width=colWidth3)
    self.tree.heading('distance2', text=f'Dist2 ({self.distUnit()})')
    self.tree.column("dist2lat", anchor=tk.E, stretch=tk.NO, width=colWidth3)
    self.tree.heading('dist2lat', text=f'Lat Dist2 ({self.distUnit()})')
    self.tree.column("dist2lon", anchor=tk.E, stretch=tk.NO, width=colWidth3)
    self.tree.heading('dist2lon', text=f'Lon Dist2 ({self.distUnit()})')
    self.tree.column("distance3", anchor=tk.E, stretch=tk.NO, width=colWidth3)
    self.tree.heading('distance3', text=f'Dist RTH ({self.distUnit()})')
    self.tree.column("altitude1", anchor=tk.E, stretch=tk.NO, width=colWidth3)
    self.tree.heading('altitude1', text=f'Alt1 ({self.distUnit()})')
    self.tree.column("altitude2", anchor=tk.E, stretch=tk.NO, width=colWidth3)
    self.tree.heading('altitude2', text=f'Alt2 ({self.distUnit()})')
    self.tree.column("speed1", anchor=tk.E, stretch=tk.NO, width=colWidth4)
    self.tree.heading('speed1', text=f'H Speed1 ({self.speedUnit()})')
    self.tree.column("speed1lat", anchor=tk.E, stretch=tk.NO, width=colWidth4)
    self.tree.heading('speed1lat', text=f'Lat S1 ({self.speedUnit()})')
    self.tree.column("speed1lon", anchor=tk.E, stretch=tk.NO, width=colWidth4)
    self.tree.heading('speed1lon', text=f'Lon S1 ({self.speedUnit()})')
    self.tree.column("speed2", anchor=tk.E, stretch=tk.NO, width=colWidth4)
    self.tree.heading('speed2', text=f'H Speed2 ({self.speedUnit()})')
    self.tree.column("speed2lat", anchor=tk.E, stretch=tk.NO, width=colWidth4)
    self.tree.heading('speed2lat', text=f'Lat S2 ({self.speedUnit()})')
    self.tree.column("speed2lon", anchor=tk.E, stretch=tk.NO, width=colWidth4)
    self.tree.heading('speed2lon', text=f'Lon S2 ({self.speedUnit()})')
    self.tree.column("speed1vert", anchor=tk.E, stretch=tk.NO, width=colWidth4)
    self.tree.heading('speed1vert', text=f'V Speed1 ({self.speedUnit()})')
    self.tree.column("speed2vert", anchor=tk.E, stretch=tk.NO, width=colWidth4)
    self.tree.heading('speed2vert', text=f'V Speed2 ({self.speedUnit()})')
    self.tree.column("satellites", anchor=tk.E, stretch=tk.NO, width=colWidth5)
    self.tree.heading('satellites', text='# Sats')
    self.tree.column("ctrllat", anchor=tk.W, stretch=tk.NO, width=colWidth2)
    self.tree.heading('ctrllat', text='Ctrl Lat')
    self.tree.column("ctrllon", anchor=tk.W, stretch=tk.NO, width=colWidth2)
    self.tree.heading('ctrllon', text='Ctrl Lon')
    self.tree.column("homelat", anchor=tk.W, stretch=tk.NO, width=colWidth2)
    self.tree.heading('homelat', text='Home Lat')
    self.tree.column("homelon", anchor=tk.W, stretch=tk.NO, width=colWidth2)
    self.tree.heading('homelon', text='Home Lon')
    self.tree.column("dronelat", anchor=tk.W, stretch=tk.NO, width=colWidth2)
    self.tree.heading('dronelat', text='Drone Lat')
    self.tree.column("dronelon", anchor=tk.W, stretch=tk.NO, width=colWidth2)
    self.tree.heading('dronelon', text='Drone Lon')
    self.tree.column("rssi", anchor=tk.W, stretch=tk.NO, width=colWidth5)
    self.tree.heading('rssi', text='RSSI')
    self.tree.column("channel", anchor=tk.W, stretch=tk.NO, width=colWidth5)
    self.tree.heading('channel', text='Chn')
    #self.tree.column("wirelessconnected", anchor=tk.W, stretch=tk.NO, width=120)
    #self.tree.heading('wirelessconnected', text='Wireless Connected')
    self.tree.column("flightctrlconnected", anchor=tk.W, stretch=tk.NO, width=colWidth2)
    self.tree.heading('flightctrlconnected', text='Drone Connected')
    self.tree.column("remoteconnected", anchor=tk.W, stretch=tk.NO, width=colWidth2)
    self.tree.heading('remoteconnected', text='Remote Connected')
    #self.tree.column("highdbm", anchor=tk.W, stretch=tk.NO, width=120)
    #self.tree.heading('highdbm', text='High Dbm')
    self.tree.column("gps", anchor=tk.W, stretch=tk.NO, width=colWidth5)
    self.tree.heading('gps', text='GPS')
    self.tree.column("inuse", anchor=tk.W, stretch=tk.NO, width=colWidth5)
    self.tree.heading('inuse', text='In Use')
    self.tree.column("motor1status", anchor=tk.E, stretch=tk.NO, width=colWidth5)
    self.tree.heading('motor1status', text=f'motor 1 Status')
    self.tree.column("motor2status", anchor=tk.E, stretch=tk.NO, width=colWidth5)
    self.tree.heading('motor2status', text=f'motor 2 Status')
    self.tree.column("motor3status", anchor=tk.E, stretch=tk.NO, width=colWidth5)
    self.tree.heading('motor3status', text=f'motor 3 Status')
    self.tree.column("motor4status", anchor=tk.E, stretch=tk.NO, width=colWidth5)
    self.tree.heading('motor4status', text=f'motor 4 Status')
    self.tree.bind('<<TreeviewSelect>>', self.item_selected)
    self.tree.grid(row=0, column=0, sticky=tk.NSEW)
    verScroll = ttk.Scrollbar(dataFrame, orient=tk.VERTICAL, command=self.tree.yview)
    self.tree.configure(yscroll=verScroll.set)
    verScroll.grid(row=0, column=1, sticky=tk.NS)
    horScroll = ttk.Scrollbar(dataFrame, orient=tk.HORIZONTAL, command=self.tree.xview)
    self.tree.configure(xscroll=horScroll.set)
    horScroll.grid(row=1, column=0, sticky=tk.EW)

    # Speed selection, Play and Stop buttons.
    playbackFrame = ttk.Frame(mapFrame, height=10, padding=(5, 0, 5, 0))
    playbackFrame.pack(fill=tk.BOTH, expand=False)
    selectPlaySpeeds = ttk.Combobox(playbackFrame, textvariable=self.selectedPlaySpeed, state="readonly", exportselection=0, width=16)
    selectPlaySpeeds.grid(row=0, column=0, sticky=tk.E, padx=7, pady=0)
    selectPlaySpeeds['values'] = (SelectablePlaybackSpeeds.REALTIME.value, SelectablePlaybackSpeeds.FAST.value, SelectablePlaybackSpeeds.FAST2.value, SelectablePlaybackSpeeds.FAST4.value, SelectablePlaybackSpeeds.FAST8.value, SelectablePlaybackSpeeds.FAST16.value, SelectablePlaybackSpeeds.FAST32.value)
    selectPlaySpeeds.bind('<<ComboboxSelected>>', self.setPlaySpeed)
    buttonPrev = ttk.Button(playbackFrame, text='<<', command=self.prevPath, width=2)
    buttonPrev.grid(row=0, column=1, sticky=tk.E, padx=0, pady=0)
    buttonPlay = ttk.Button(playbackFrame, text='|>', command=self.play, width=2)
    buttonPlay.grid(row=0, column=2, sticky=tk.E, padx=0, pady=0)
    buttonNext = ttk.Button(playbackFrame, text='>>', command=self.nextPath, width=2)
    buttonNext.grid(row=0, column=3, sticky=tk.E, padx=0, pady=0)

    if (not self.tinyScreen):
      # Controller and Home selection checkboxes.
      markerCtrlView = ttk.Checkbutton(playbackFrame, text='Controller', command=self.setMarkerCtrl, variable=self.showMarkerCtrl, onvalue='Y', offvalue='N')
      markerCtrlView.grid(row=0, column=5, sticky=tk.E, padx=4, pady=0)
      markerHomeView = ttk.Checkbutton(playbackFrame, text='Home', command=self.setMarkerHome, variable=self.showMarkerHome, onvalue='Y', offvalue='N')
      markerHomeView.grid(row=0, column=6, sticky=tk.E, padx=4, pady=0)

    if (not self.smallScreen):
      # Current drone location metrics.
      self.labelFlight = ttk.Label(playbackFrame, text='')
      self.labelFlight.grid(row=0, column=7, sticky=tk.W, padx=2, pady=0)

    # Map and Flight selections.
    fileInfoFrame = ttk.Frame(mapFrame, height=10, padding=(5, 0, 5, 5))
    fileInfoFrame.pack(fill=tk.BOTH, expand=False)
    selectTileSource = ttk.Combobox(fileInfoFrame, textvariable=self.selectedTile, state="readonly", exportselection=0, width=16)
    selectTileSource.grid(row=0, column=0, sticky=tk.E, padx=7, pady=0)
    selectTileSource['values'] = (SelectableTileServer.OPENSTREETMAP.value, SelectableTileServer.GOOGLE_STANDARD.value, SelectableTileServer.GOOGLE_SATELLITE.value, SelectableTileServer.OPEN_TOPO.value)
    selectTileSource.bind('<<ComboboxSelected>>', self.setTileSource)
    self.selectedPath = tk.StringVar()
    self.selectPath = ttk.Combobox(fileInfoFrame, textvariable=self.selectedPath, state="readonly", exportselection=0, width=14)
    self.selectPath.grid(row=0, column=1, sticky=tk.E, padx=7, pady=0)
    self.selectPath.bind('<<ComboboxSelected>>', self.choosePath)

    if (not self.tinyScreen):
      # Flight Path and All Metrics selection checkboxes.
      self.showPath = tk.StringVar()
      pathView = ttk.Checkbutton(fileInfoFrame, text='Flight Paths', command=self.setPathView, variable=self.showPath, onvalue='Y', offvalue='N')
      pathView.grid(row=0, column=2, sticky=tk.E, padx=2, pady=0)
      self.showPath.set('Y')
      selectTableView = ttk.Combobox(fileInfoFrame, textvariable=self.selectedTableView, state="readonly", exportselection=0, width=16)
      selectTableView.grid(row=0, column=3, sticky=tk.E, padx=4, pady=0)
      selectTableView['values'] = (SelectableMetrics.BASIC.value, SelectableMetrics.ADVANCED.value, SelectableMetrics.DIAGNOSTICS.value)
      selectTableView.bind('<<ComboboxSelected>>', self.setTableView)
    else:
      optionsFrame = ttk.Frame(mapFrame, height=10, padding=(5, 0, 5, 0))
      optionsFrame.pack(fill=tk.BOTH, expand=False)
      # Controller and Home selection checkboxes.
      markerCtrlView = ttk.Checkbutton(optionsFrame, text='Ctrl', command=self.setMarkerCtrl, variable=self.showMarkerCtrl, onvalue='Y', offvalue='N')
      markerCtrlView.grid(row=0, column=0, sticky=tk.E, padx=4, pady=0)
      markerHomeView = ttk.Checkbutton(optionsFrame, text='Home', command=self.setMarkerHome, variable=self.showMarkerHome, onvalue='Y', offvalue='N')
      markerHomeView.grid(row=0, column=1, sticky=tk.E, padx=4, pady=0)
      # Flight Path and All Metrics selection checkboxes.
      self.showPath = tk.StringVar()
      pathView = ttk.Checkbutton(optionsFrame, text='Paths', command=self.setPathView, variable=self.showPath, onvalue='Y', offvalue='N')
      pathView.grid(row=0, column=2, sticky=tk.E, padx=2, pady=0)
      self.showPath.set('Y')
      selectTableView = ttk.Combobox(optionsFrame, textvariable=self.selectedTableView, state="readonly", exportselection=0, width=16)
      selectTableView.grid(row=0, column=3, sticky=tk.E, padx=4, pady=0)
      selectTableView['values'] = (SelectableMetrics.BASIC.value, SelectableMetrics.ADVANCED.value, SelectableMetrics.DIAGNOSTICS.value)
      selectTableView.bind('<<ComboboxSelected>>', self.setTableView)

    if (not self.smallScreen):
      # Max values of the flights.
      self.labelFile = ttk.Label(fileInfoFrame, text='')
      self.labelFile.grid(row=0, column=4, sticky=tk.W, padx=2, pady=0)
    else:
      if (not self.tinyScreen):
        # Max values of the flights.    
        flightInfoFrame1 = ttk.Frame(mapFrame, height=10, padding=(5, 0, 5, 5))
        flightInfoFrame1.pack(fill=tk.BOTH, expand=False)
        self.labelFile = ttk.Label(flightInfoFrame1, text='')
        self.labelFile.grid(row=0, column=0, sticky=tk.W, padx=2, pady=0)

      # Current drone location metrics.      
      flightInfoFrame2 = ttk.Frame(mapFrame, height=10, padding=(5, 0, 5, 5))
      flightInfoFrame2.pack(fill=tk.BOTH, expand=False)
      self.labelFlight = ttk.Label(flightInfoFrame2, text='')
      self.labelFlight.grid(row=0, column=0, sticky=tk.W, padx=2, pady=0)

    self.map_widget = tkintermapview.TkinterMapView(mapFrame, corner_radius=0)

    # Adjust map buttons, if needed.
    adjMapButtonWidth = self.scaledWidth(self.map_widget.button_zoom_in.width)
    if (self.map_widget.button_zoom_in.width != adjMapButtonWidth):
      self.map_widget.button_zoom_in.width = adjMapButtonWidth
      self.map_widget.button_zoom_in.height = adjMapButtonWidth
      self.map_widget.button_zoom_in.canvas_position = (20, 20)
      self.map_widget.button_zoom_in.map_widget.canvas.delete(self.map_widget.button_zoom_in.canvas_rect)
      self.map_widget.button_zoom_in.map_widget.canvas.delete(self.map_widget.button_zoom_in.canvas_text)
      self.map_widget.button_zoom_in.draw()
      self.map_widget.button_zoom_out.width = adjMapButtonWidth
      self.map_widget.button_zoom_out.height = adjMapButtonWidth
      self.map_widget.button_zoom_out.canvas_position = (20, 20 + adjMapButtonWidth + self.map_widget.button_zoom_in.border_width + 8)
      self.map_widget.button_zoom_out.map_widget.canvas.delete(self.map_widget.button_zoom_out.canvas_rect)
      self.map_widget.button_zoom_out.map_widget.canvas.delete(self.map_widget.button_zoom_out.canvas_text)
      self.map_widget.button_zoom_out.draw()

    self.map_widget.pack(fill=tk.BOTH, expand=True)

    self.reset();


if __name__ == '__main__':
  extract = ExtractFlightData()
  extract.mainloop()
