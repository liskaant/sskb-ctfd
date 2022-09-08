function htmlEntities(string) {
  return $("<div/>")
    .text(string)
    .html();
}

function cumulativeSum(arr) {
  let result = arr.concat();
  for (let i = 0; i < arr.length; i++) {
    result[i] = arr.slice(0, i + 1).reduce(function(p, i) {
      return p + i;
    });
  }
  return result;
}

function colorHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
    hash = hash & hash;
  }
  // Range calculation
  // diff = max - min;
  // x = ((hash % diff) + diff) % diff;
  // return x + min;
  // Calculate HSL values
  // Range from 0 to 360
  let h = ((hash % 360) + 360) % 360;
  // Range from 75 to 100
  let s = (((hash % 25) + 25) % 25) + 75;
  // Range from 40 to 60
  let l = (((hash % 20) + 20) % 20) + 40;
  return `hsl(${h}, ${s}%, ${l}%)`;
}

const buildGraphData = (places) => {
  const teams = Object.keys(places);
  if (teams.length === 0) {
    return false;
  }

  const option = {
    title: {
      left: "center",
      text: "Top 10 " + (CTFd.config.userMode === "teams" ? "Teams" : "Users")
    },
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "cross"
      }
    },
    legend: {
      type: "scroll",
      orient: "horizontal",
      align: "left",
      bottom: 35,
      data: []
    },
    toolbox: {
      feature: {
        dataZoom: {
          yAxisIndex: "none"
        },
        saveAsImage: {}
      }
    },
    grid: {
      containLabel: true
    },
    xAxis: [
      {
        type: "time",
        boundaryGap: false,
        data: []
      }
    ],
    yAxis: [
      {
        type: "value"
      }
    ],
    dataZoom: [
      {
        id: "dataZoomX",
        type: "slider",
        xAxisIndex: [0],
        filterMode: "filter",
        height: 20,
        top: 35,
        fillerColor: "rgba(233, 236, 241, 0.4)"
      }
    ],
    series: []
  };

  for (let i = 0; i < teams.length; i++) {
    const team_score = [];
    const times = [];
    for (let j = 0; j < places[teams[i]]["solves"].length; j++) {
      team_score.push(places[teams[i]]["solves"][j].value);
      const date = dayjs(places[teams[i]]["solves"][j].date);
      times.push(date.toDate());
    }

    const total_scores = cumulativeSum(team_score);
    var scores = times.map(function(e, i) {
      return [e, total_scores[i]];
    });

    option.legend.data.push(places[teams[i]]["name"]);

    const data = {
      name: places[teams[i]]["name"],
      type: "line",
      label: {
        normal: {
          position: "top"
        }
      },
      itemStyle: {
        normal: {
          color: colorHash(places[teams[i]]["name"] + places[teams[i]]["id"])
        }
      },
      data: scores
    };
    option.series.push(data);
  }

  return option;
};

const createGraph = (graph, places) => {
  const option = buildGraphData(places);

  if (option === false) {
    // Replace spinner
    graph.html(
      '<h3 class="opacity-50 text-center w-100 justify-content-center align-self-center">No solves yet</h3>'
    );
    return;
  }

  graph.empty(); // Remove spinners
  let chart = echarts.init(graph.get(0));
  chart.setOption(option);

  $(window).on("resize", function() {
    if (chart != null && chart != undefined) {
      chart.resize();
    }
  });
};

window.addEventListener('load', () => {
    window.updateScoreboard = () => {
        $("[data-score-graph]").removeAttr('_echarts_instance_').empty();
        setTimeout(() => {
            $("[data-score-graph]").removeAttr('_echarts_instance_').empty().each((i, el) => createGraph($(el), JSON.parse(el.getAttribute('data-score-graph'))));
        }, 200);
    };

    window.updateScoreboard();
})
