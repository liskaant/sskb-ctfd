window.addEventListener("load", () => {
	const urlSplit = window.location.href.split("/").filter(x => x);
	const urlLast = urlSplit[urlSplit.length - 1];
	const categoryUrl = urlLast === "scoreboard" ? "" : `/${urlLast}`;

	function defer() {
		const deferred = { resolve: undefined, reject: undefined };
		deferred.promise = new Promise((resolve, reject) => {
			deferred.resolve = resolve;
			deferred.reject = reject;
		});
		return deferred;
	}

	CTFd.api.get_scoreboard_list = function() {
		const deferred = defer();
		CTFd.api.request("GET", `${CTFd.api.domain}/scoreboard${categoryUrl}`, {}, {}, {
			"Accept": "application/json",
			"Content-Type": "application/json",
		}, {}, {}, deferred);
		return deferred.promise;
	}

	CTFd.api.get_scoreboard_detail = function(parameters) {
		const deferred = defer();
		CTFd.api.request("GET", `${CTFd.api.domain}/scoreboard/top/${parameters.count}${categoryUrl}`, {}, {}, {
			"Accept": "application/json",
			"Content-Type": "application/json",
		}, {}, {}, deferred);
		return deferred.promise;
	}
});
