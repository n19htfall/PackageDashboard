import type { Ref } from 'vue'
import { type ECOption } from '~/composables/echarts'

interface chartDataValues {
  xAxisData: Array<string>
  commitsData: Array<number>
  commentData: Array<number>
  issuesData: Array<number>
  prsData: Array<number>
  starsData: Array<number>
  tagsData: Array<number>
}

interface chartConfig {
  chartData: Array<number>
  chartAxis: Array<string>
  chartName: string
}

export function updateBarChartOptions(chartOptions: Ref<ECOption>, chartConfig: chartConfig) {
  chartOptions.value = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985',
        },
      },
    },
    // legend: {
    //  data: [chartConfig.chartLegend]
    // },
    grid: {
      left: '2%',
      right: '2%',
      bottom: '2%',
      containLabel: true,
    },
    xAxis: [
      {
        type: 'category',
        data: chartConfig.chartAxis,
      },
    ],
    yAxis: [
      {
        type: 'value',
      },
    ],
    series: [
      {
        color: '#8e9dff',
        name: chartConfig.chartName,
        type: 'bar',
        data: chartConfig.chartData,
      },
    ],
  }
}

export function updateLineChartOptions(lineOptions: Ref<ECOption>, chartData: chartDataValues) {
  lineOptions.value = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985',
        },
      },
    },
    legend: {
      data: ['Commits', 'Comments', 'Issues', 'Pull Requests', 'Stars', 'Tags'],
    },
    grid: {
      left: '2%',
      right: '2%',
      bottom: '2%',
      containLabel: true,
    },
    xAxis: [
      {
        type: 'category',
        boundaryGap: false,
        data: chartData.xAxisData,
      },
    ],
    yAxis: [
      {
        type: 'value',
      },
    ],
    series: [
      {
        color: '#8e9dff',
        name: 'Commits',
        type: 'line',
        smooth: true,
        stack: 'Total',
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0.25,
                color: '#8e9dff',
              },
              {
                offset: 1,
                color: '#fff',
              },
            ],
          },
        },
        emphasis: {
          focus: 'series',
        },
        data: chartData.commitsData,
      },
      {
        color: '#26deca',
        name: 'Comments',
        type: 'line',
        smooth: true,
        stack: 'Total',
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0.25,
                color: '#26deca',
              },
              {
                offset: 1,
                color: '#fff',
              },
            ],
          },
        },
        emphasis: {
          focus: 'series',
        },
        data: chartData.commentData,
      },
      {
        color: '#641E16',
        name: 'Issues',
        type: 'line',
        smooth: true,
        stack: 'Total',
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0.25,
                color: '#641E16',
              },
              {
                offset: 1,
                color: '#fff',
              },
            ],
          },
        },
        emphasis: {
          focus: 'series',
        },
        data: chartData.issuesData,
      },
      {
        color: '#512E5F',
        name: 'Pull Requests',
        type: 'line',
        smooth: true,
        stack: 'Total',
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0.25,
                color: '#512E5F',
              },
              {
                offset: 1,
                color: '#fff',
              },
            ],
          },
        },
        emphasis: {
          focus: 'series',
        },
        data: chartData.prsData,
      },
      {
        color: '#0E6251',
        name: 'Stars',
        type: 'line',
        smooth: true,
        stack: 'Total',
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0.25,
                color: '#0E6251',
              },
              {
                offset: 1,
                color: '#fff',
              },
            ],
          },
        },
        emphasis: {
          focus: 'series',
        },
        data: chartData.starsData,
      },
      {
        color: '#F1C40F',
        name: 'Tags',
        type: 'line',
        smooth: true,
        stack: 'Total',
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0.25,
                color: '#F1C40F',
              },
              {
                offset: 1,
                color: '#fff',
              },
            ],
          },
        },
        emphasis: {
          focus: 'series',
        },
        data: chartData.tagsData,
      },
    ],
  }
}
