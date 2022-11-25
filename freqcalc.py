import decimal
from collections import namedtuple
import re

import wx

import freqlists

FrequencyObject = namedtuple("FrequencyObject", ["name", "frequency", "frequencyRaw"])


class Band:
    def __init__(
        self,
        bandName: tuple[str, str],
        startRange: float,
        freqStep: float,
        channelsAmount: int,
        freqFormat: str,
        bandDivider: int = None,
    ):
        self.name, self.tip = bandName
        (
            self.startRange,
            self.freqStep,
            self.channelsAmount,
            self.freqFormat,
            self.bandDivider,
        ) = (startRange, freqStep, channelsAmount, freqFormat, bandDivider)

    def __getitem__(self, channel: int) -> FrequencyObject:
        result = self.startRange + (self.freqStep * channel)
        bandName = self.name
        if "/" in self.name:
            if channel < self.bandDivider - 1:
                bandName = self.name.partition("/")[0]
            else:
                bandName = self.name.partition("/")[2]
        return FrequencyObject(
            name=f"{bandName} {channel + 1}",
            frequency=self.freqFormat % result,
            frequencyRaw=result,
        )

    def __len__(self):
        return self.channelsAmount

    def __iter__(self):
        self.iterOffset = 0
        return self

    def __next__(self) -> FrequencyObject:
        if self.iterOffset < len(self):
            retval = self[self.iterOffset]
            self.iterOffset += 1
            return retval
        raise StopIteration


class StaticBand(Band):
    def __init__(
        self, bandName: tuple[str, str], freqFormat: str, frequencies: list[float]
    ):
        if len(frequencies) < 1:
            raise ValueError("Frequencies list must not be empty")
        self.name, self.tip = bandName
        self.startRange = frequencies[0]
        self.channelsAmount = len(frequencies)
        self.freqFormat = freqFormat
        self.frequencies = frequencies

    def __getitem__(self, channel: int) -> FrequencyObject:
        result = self.frequencies[channel]
        return FrequencyObject(
            name=f"{self.name} {channel + 1}",
            frequency=self.freqFormat % result,
            frequencyRaw=result,
        )


bandsList = [
    Band(
        bandName=("LPD", "Low Power Device"),
        startRange=433.075,
        freqStep=0.025,
        channelsAmount=69,
        freqFormat="%.3f",
    ),
    Band(
        bandName=("PMR", "Private Mobile Radio"),
        startRange=446.00625,
        freqStep=0.0125,
        channelsAmount=8,
        freqFormat="%.5f",
    ),
    Band(
        bandName=("FRS/GMRS", "Family Radio Service"),
        startRange=462.5625,
        freqStep=0.025,
        channelsAmount=22,
        freqFormat="%.4f",
        bandDivider=15,
    ),
    StaticBand(
        bandName=("CB eu a", "CB European standard A"),
        freqFormat="%.3f",
        frequencies=freqlists.CB_EU_A,
    ),
]


class ChanToFreqTab(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        parent.AddPage(self, "Канал в частоту")
        tabSizer = wx.BoxSizer(wx.HORIZONTAL)
        bandsChooserPanel = wx.Panel(self)
        bandsChooserSizer = wx.BoxSizer(wx.VERTICAL)
        self.bandsChooser = wx.RadioBox(
            bandsChooserPanel,
            wx.ID_ANY,
            "Диапазон:",
            choices=[band.name + f" ({band.tip})" for band in bandsList],
            style=wx.RA_SPECIFY_ROWS,
        )
        bandsChooserSizer.Add(self.bandsChooser, wx.EXPAND)
        bandsChooserPanel.SetSizer(bandsChooserSizer)
        self.bandsChooser.SetToolTip(
            "Выберите диапазон, частоту которого вы хотите увидеть. Поддерживаются диапазоны {}.".format(
                ", ".join(([band.tip for band in bandsList]))
            )
        )
        self.bandsChooser.SetSelection(0)
        self.bandsChooser.Bind(wx.EVT_RADIOBOX, self.onBandSelected)
        tabSizer.Add(bandsChooserPanel, wx.EXPAND)
        channelChooser = wx.Panel(self)
        channelsSizer = wx.BoxSizer(wx.VERTICAL)
        channelsSizer.Add(wx.StaticText(channelChooser, wx.ID_ANY, "Канал:"), wx.EXPAND)
        self.channelsCombo = wx.ComboBox(
            channelChooser,
            wx.ID_ANY,
            choices=[
                channel.name for channel in bandsList[self.bandsChooser.GetSelection()]
            ],
            style=wx.CB_READONLY,
        )
        self.channelsCombo.SetSelection(0)
        self.channelsCombo.Bind(wx.EVT_COMBOBOX, self.onChannelSelected)
        self.channelsCombo.SetToolTip("Выберите канал выбранного диапазона.")
        channelsSizer.Add(self.channelsCombo, wx.EXPAND)
        channelChooser.SetSizer(channelsSizer)
        tabSizer.Add(channelChooser, wx.EXPAND)
        resultArea = wx.Panel(self)
        freqSizer = wx.BoxSizer(wx.VERTICAL)
        freqSizer.Add(wx.StaticText(resultArea, wx.ID_ANY, "Частота:"), wx.EXPAND)
        self.frequencyResult = wx.TextCtrl(
            resultArea,
            wx.ID_ANY,
            bandsList[self.bandsChooser.GetSelection()][
                self.channelsCombo.GetSelection()
            ].frequency
            + " МГц",
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP,
        )
        freqSizer.Add(self.frequencyResult, wx.EXPAND)
        actionsArea = wx.Panel(resultArea)
        actBtnsSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.copyFrequencyButton = wx.Button(
            actionsArea, wx.ID_ANY, "Копировать частоту"
        )
        self.copyFrequencyButton.Bind(wx.EVT_BUTTON, self.onActionCopy)
        actBtnsSizer.Add(self.copyFrequencyButton, wx.EXPAND)
        self.copyBFFrequencyButton = wx.Button(
            actionsArea, wx.ID_ANY, "Копировать частоту для BF480"
        )
        self.copyBFFrequencyButton.Bind(wx.EVT_BUTTON, self.onActionBFCopy)
        self.copyBFFrequencyButton.SetToolTip(
            "Программа BF480 для прошивки радиостанций Baofeng принимает частоты, разделенные не точкой, как это ожидалось бы, а запятой."
        )
        actBtnsSizer.Add(self.copyBFFrequencyButton, wx.EXPAND)
        actionsArea.SetSizer(actBtnsSizer)
        resultArea.SetSizer(freqSizer)
        self.SetSizer(tabSizer)
        self.clipboard = wx.Clipboard()

    def onBandSelected(self, _):
        self.channelsCombo.Clear()
        self.channelsCombo.AppendItems(
            [channel.name for channel in bandsList[self.bandsChooser.GetSelection()]]
        )
        self.channelsCombo.SetSelection(0)
        self.onChannelSelected()
        return True

    def onChannelSelected(self, _=None):
        selectedBand = self.bandsChooser.GetSelection()
        selectedChannel = self.channelsCombo.GetSelection()
        frequency = bandsList[selectedBand][selectedChannel].frequency
        self.frequencyResult.SetValue(f"{frequency} МГц")
        return True

    def onActionCopy(self, _):
        if wx.TheClipboard.Open():
            self.clipboard.SetData(
                wx.TextDataObject(
                    bandsList[self.bandsChooser.GetSelection()][
                        self.channelsCombo.GetSelection()
                    ].frequency
                )
            )
            wx.TheClipboard.Close()

    def onActionBFCopy(self, _):
        if wx.TheClipboard.Open():
            self.clipboard.SetData(
                wx.TextDataObject(
                    re.sub(
                        "[.]",
                        ",",
                        bandsList[self.bandsChooser.GetSelection()][
                            self.channelsCombo.GetSelection()
                        ].frequency,
                    )
                )
            )
            wx.TheClipboard.Close()


class FreqToChanTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        parent.AddPage(self, "Частоту в канал")
        tabSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(tabSizer)
        freqInputArea = wx.Panel(self)
        freqFieldSizer = wx.BoxSizer(wx.VERTICAL)
        freqInputArea.SetSizer(freqFieldSizer)
        freqFieldSizer.Add(wx.StaticText(freqInputArea, wx.ID_ANY, "Частота:"))
        self.freqField = wx.TextCtrl(freqInputArea)
        self.freqField.Bind(wx.EVT_TEXT, self.onFrequencyProvided)
        self.freqField.SetToolTip(
            "Введите здесь частоту одного из поддерживаемых диапазонов. Поддерживается любой формат разделения десятичных частот."
        )
        freqFieldSizer.Add(self.freqField, wx.EXPAND)
        resultArea = wx.Panel(self)
        resultSizer = wx.BoxSizer(wx.VERTICAL)
        resultArea.SetSizer(resultSizer)
        resultSizer.Add(wx.StaticText(resultArea, wx.ID_ANY, "Канал:"), wx.EXPAND)
        self.resultField = wx.TextCtrl(
            resultArea,
            wx.ID_ANY,
            "",
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP,
        )
        self.resultField.AppendText(
            "Введите частоту слева, чтобы узнать ее диапазон и канал. Поддерживаются диапазоны "
        )
        self.resultField.AppendText(
            re.sub(
                r"(.+), (.+)$",
                r"\1 и \2.",
                ", ".join([band.tip + f" ({band.name})" for band in bandsList]),
            )
        )
        resultSizer.Add(self.resultField, wx.EXPAND)

    def onFrequencyProvided(self, event):
        freqProvided = event.GetEventObject().GetValue()
        decimal.getcontext().prec = 6
        if re.search(r"\D", freqProvided):
            freqProvided = re.sub(r"^(\d+)\D|\W|\s(\d+)", r"\1.\2", freqProvided)
        try:
            # We have to use this intermediate float conversion to avoid mistakes in Decimal with float comparison later
            freqProvided = decimal.Decimal(float(freqProvided))
        except (decimal.InvalidOperation, ValueError):
            self.resultField.ChangeValue("Введите число")
            return True
        for band in bandsList:
            if isinstance(band, StaticBand):
                lastChannel: FrequencyObject | None = None
                prevDifference: decimal.Decimal | None = None
                for channel in band:
                    if freqProvided == channel.frequencyRaw:
                        self.resultField.ChangeValue(channel.name)
                        return True
                    else:
                        currentDifference = abs(
                            freqProvided - decimal.Decimal(channel.frequencyRaw)
                        )
                        if (
                            prevDifference is None
                            or currentDifference <= prevDifference
                        ):
                            prevDifference = currentDifference
                            lastChannel = channel
                self.resultField.ChangeValue(
                    f"Ближе к {lastChannel.name}, частота которого {lastChannel.frequency}"
                )
                return True
            else:
                if (
                    (band.startRange - band.freqStep)
                    <= freqProvided
                    <= band[len(band) + 1].frequencyRaw
                ):
                    preChannel = (
                        (freqProvided - decimal.Decimal(band.startRange))
                        / decimal.Decimal(band.freqStep)
                    ) + 1
                    if round(preChannel) < 1:
                        preChannel = 0.9
                    elif round(preChannel) > len(band):
                        preChannel = len(band) + 0.1
                    if int(preChannel) == preChannel:
                        self.resultField.ChangeValue(band[round(preChannel) - 1].name)
                    else:
                        self.resultField.ChangeValue(
                            f"Ближе к {band[round(preChannel) - 1].name}, частота которого {band[round(preChannel) - 1].frequency} МГц"
                        )
                    return True
        self.resultField.ChangeValue("Ни в одном известном диапазоне")
        return True


class AppWindow(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(
            None,
            title="Калькулятор частот",
            pos=(wx.Center, wx.Center),
            size=(640, 480),
        )
        self.tabs = wx.Notebook(self)
        self.chanToFreq = ChanToFreqTab(self.tabs)
        self.freqToChanTab = FreqToChanTab(self.tabs)
        self.Bind(wx.EVT_CHAR_HOOK, self.keyProcess)

    def keyProcess(self, event: wx.KeyEvent):
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self.Close()
            return True
        event.Skip()


program = wx.App()
frame = AppWindow()
program.SetTopWindow(frame)
frame.Show(True)

program.MainLoop()
