import { createContext, useContext } from 'react'

// Lets any ticker table open the chart, without passing a function through every component.
// openChart(ticker, element): element gets focus back when the chart closes.
export const ChartContext = createContext(() => {})

export const useOpenChart = () => useContext(ChartContext)
