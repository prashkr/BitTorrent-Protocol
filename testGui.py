def GUI():
    app = wx.App()
    Example(None, title="Distributed Bittorent")
    app.MainLoop()

class MyProgressDialog(wx.Dialog):
    """"""
 
    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        wx.Dialog.__init__(self, None, title="Progress")
        self.count = 0
 
        self.progress = wx.Gauge(self, range=20)
 
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.progress, 0, wx.EXPAND)
        self.SetSizer(sizer)
 
        # create a pubsub listenerwx.
        CallAfter(Publisher().sendMessage, "update", "")
        Publisher().subscribe(self.updateProgress, "update")
 
    #----------------------------------------------------------------------
    def updateProgress(self, msg):
        """
        Update the progress bar
        """
        self.count += 1
 
        if self.count >= 20:
            self.Destroy()
 
        self.progress.SetValue(self.count)

class Example(wx.Frame):

    def __init__(self, parent, title):    
        super(Example, self).__init__(parent, title=title, 
            size=(450, 350))

        self.InitUI()
        self.Centre()
        self.Show()     

    def OnButton_FrameHandler(self,event):
        print "Hello"
        openFileDialog = wx.FileDialog(self, "Open Torrent file", "", "",
                                       "Torrent files (*.torrent)|*.torrent", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if openFileDialog.ShowModal() == wx.ID_CANCEL:
            return    
        else:
            paths = openFileDialog.GetPaths()
            print paths[0] 
     #   input_stream = wx.FileInputStream(openFileDialog.GetPath())
        
        # f = open(paths[0],"r")
#         initialize(paths[0])
#         try:
#             start_new_thread(recvMessage,(myHost,myPort,peerList))  
# #     #   start_new_thread(sendMessage,(host,port,peerList))
#         except:
#             print "Error: unable to start thread"
        # recvMessage(myHost,myPort,peerList)
        # print f.read(1024)
        # f.close()
     #   dlg = MyProgressDialog()
      #  dlg.ShowModal()
        # self.createProgressBar()
        '''if not input_stream.IsOk():
            wx.LogError("Cannot open file '%s'."%openFileDialog.GetPath())
            return'''

    def OnClickExit(self,event):
        running = False


    def createProgressBar(self):
        self.count = 0
        self.progress = wx.Gauge(self, range=20)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(self.progress,2,  
            flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)
        Publisher().subscribe(self.updateProgress, "update")
    def updateProgress(self, msg):
        """
        Update the progress bar
        """
        self.count += 1
 
        if self.count >= 20:
            self.Destroy()
 
        self.progress.SetValue(self.count)
                        
    def InitUI(self):
      
        panel = wx.Panel(self)
        
        sizer = wx.GridBagSizer(5, 5)

        text1 = wx.StaticText(panel, label="BITTORRENT v1.0")
        sizer.Add(text1, pos=(0, 0), flag=wx.TOP|wx.LEFT|wx.BOTTOM, 
            border=15)

        icon = wx.StaticBitmap(panel, bitmap=wx.Bitmap('exec.png'))
        sizer.Add(icon, pos=(0, 4), flag=wx.TOP|wx.RIGHT|wx.ALIGN_RIGHT, 
            border=5)

        line = wx.StaticLine(panel)
        sizer.Add(line, pos=(1, 0), span=(1, 5), 
            flag=wx.EXPAND|wx.BOTTOM, border=10)

        self.text2 = wx.StaticText(panel, label="Name")
        sizer.Add(text2, pos=(2, 0), flag=wx.LEFT, border=10)

        tc1 = wx.TextCtrl(panel)
        sizer.Add(tc1, pos=(2, 1), span=(1, 3), flag=wx.TOP|wx.EXPAND)


        self.text3 = wx.StaticText(panel, label="Torrent File")
        sizer.Add(text3, pos=(3, 0), flag=wx.LEFT|wx.TOP, border=10)

        tc2 = wx.TextCtrl(panel)
        sizer.Add(tc2, pos=(3, 1), span=(1, 3), flag=wx.TOP|wx.EXPAND, 
            border=5)

        # self.text1 = wx.TextCtrl(id=wxID_FRAME1TEXT1, name=u'text1',
        #       parent=self.panel1, pos=wx.Point(268, 139), size=wx.Size(103, 25),
        #       style=0, value=u'enter')

        button1 = wx.Button(panel, label="Browse...")
        sizer.Add(button1, pos=(3, 4), flag=wx.TOP|wx.RIGHT, border=5)
        self.Bind( wx.EVT_BUTTON, self.OnButton_FrameHandler, button1 )

        '''text4 = wx.StaticText(panel, label="Extends")
        sizer.Add(text4, pos=(4, 0), flag=wx.TOP|wx.LEFT, border=10)

        combo = wx.ComboBox(panel)
        sizer.Add(combo, pos=(4, 1), span=(1, 3), 
            flag=wx.TOP|wx.EXPAND, border=5)'''

        '''button2 = wx.Button(panel, label="Browse...")
        sizer.Add(button2, pos=(4, 4), flag=wx.TOP|wx.RIGHT, border=5)'''

        sb = wx.StaticBox(panel, label="Optional Attributes")

        boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
        boxsizer.Add(wx.CheckBox(panel, label="Public"), 
            flag=wx.LEFT|wx.TOP, border=5)
        boxsizer.Add(wx.CheckBox(panel, label="Generate Default Constructor"),
            flag=wx.LEFT, border=5)
        boxsizer.Add(wx.CheckBox(panel, label="Generate Main Method"), 
            flag=wx.LEFT|wx.BOTTOM, border=5)
        sizer.Add(boxsizer, pos=(5, 0), span=(1, 5), 
            flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT , border=10)

        button3 = wx.Button(panel, label='Help')
        sizer.Add(button3, pos=(7, 0), flag=wx.LEFT, border=10)

        button4 = wx.Button(panel, label="Ok")
        sizer.Add(button4, pos=(7, 3))

        button5 = wx.Button(panel, label="Exit")
        sizer.Add(button5, pos=(7, 4), span=(1, 1),  
            flag=wx.BOTTOM|wx.RIGHT, border=5)
        self.Bind( wx.EVT_BUTTON, self.OnClickExit, button5 )

        sizer.AddGrowableCol(2)
        
        panel.SetSizer(sizer)


if __name__ == '__main__':

    try:
        start_new_thread(GUI, ())
    except:
        print "Error: unable to start thread"
while 1:
    pass