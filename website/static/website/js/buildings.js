var buildings = JSON.parse(document.getElementById('buildings').textContent);
var profile = localStorage.getItem('profile_json');
var siege_rewards = JSON.parse(document.getElementById('siege').textContent);
var gw_rewards = JSON.parse(document.getElementById('gw').textContent);

$( document ).ready(function() {
    for (const [key, value] of Object.entries(buildings)) {
        let upgrade_id = "#" + key + " #upgrade";
        let upgrade_max_id = "#" + key + " #upgrade-max";

        let sum = value.reduce((a, b) => a + b, 0);
        $(upgrade_id).text(value[0]);
        $(upgrade_max_id).text(sum);
    }

    if(!profile){
        $('#profile-upload').html("<h2>No uploaded profile available. Please, <a href='" + upload_url + "'>upload your profile</a> first if you want to use all calculator functionalities.</h2>")
    }
    else{
        let decos = JSON.parse(profile).deco_list;
        for(var deco_id in decos){
            let deco = decos[deco_id];
            let id_row = "#id_" + deco.master_id;
            let level_id = id_row + " #level";
            let upgrade_id = id_row + " #upgrade";
            let upgrade_max_id = id_row + " #upgrade-max";
            let level = deco.level;
            var sum, next_upgrade;

            if(level == 10) { 
                sum = 0; 
                next_upgrade = 0; 
                $(id_row).addClass("building-done");
            }
            else{
                let upgrades = buildings['id_' + deco.master_id].slice(level)
                sum = upgrades.reduce((a, b) => a + b, 0);
                next_upgrade = upgrades[0]
            }
            $(level_id).text(level);
            $(upgrade_id).text(next_upgrade);
            $(upgrade_max_id).text(sum);
        }
    }
    calculateArenaDays();
    calculateGuildDays();
});

function loading(done=false) {
    let text = "Please wait, calculating days...";
    if(done){ text = ""; }
    $("#loading").text(text);
}

$('#arena-ranking').on('change', function() {
    if($('#arena-wings').val() < 20){
        return;
    }
    loading();
    calculateArenaDays().then(loading(true)); 
});
$('#arena-wings').bind('input', function(){
    if($('#arena-wings').val() < 20){
        return;
    }
    loading();
    calculateArenaDays().then(loading(true)); 
});

async function calculateArenaDays(){
    let arena_wings = $('#arena-wings').val();
    let arena_ranking = $('#arena-ranking').val();
    if(!arena_wings || arena_wings == "" ){ $('#arena-wings').val(0); arena_wings = 0 }

    let points_per_day = arena_wings * arena_ranking // wings per day * arena points per win, assume farming (all wins)

    for (const [key, value] of Object.entries(buildings)) {
        if($("#" + key + " #area").text() != "Arena"){ continue; }

        let upgrade_id = "#" + key + " #upgrade";
        let upgrade_max_id = "#" + key + " #upgrade-max";
        let days_id = "#" + key + " #days";
        let days_max_id = "#" + key + " #days-max";

        let upgrade_next = parseInt($(upgrade_id).text());
        let upgrade_max = parseInt($(upgrade_max_id).text());
        let days = 0;
        let days_max = 0;

        while(upgrade_next > 0){
            if(days % 7 == 0){ upgrade_next += 180; upgrade_next -= 60; } // devilmon; arena league reward
            upgrade_next -= points_per_day
            days += 1;
        }
        while(upgrade_max > 0){
            if(days_max % 7 == 0){ upgrade_max += 180; upgrade_max -= 60; } // devilmon; arena league reward
            upgrade_max -= points_per_day
            days_max += 1;
        }
        $(days_id).text(days);
        $(days_max_id).text(days_max);
    }
}

$('#guild-ranking').on('change', function() {
    loading();
    calculateGuildDays().then(loading(true)); 
});
$('#siege-ranking').on('change', function() {
    loading();
    calculateGuildDays().then(loading(true)); 
});
$('input[name="siege-first"]').on('change', function() {
    loading();
    calculateGuildDays().then(loading(true)); 
});
$('input[name="siege-second"]').on('change', function() {
    loading();
    calculateGuildDays().then(loading(true)); 
});
$('#guild-wings').bind('input', function(){
    loading();
    calculateGuildDays().then(loading(true)); 
});

async function calculateGuildDays(){
    let gw = gw_rewards[$("#guild-ranking").val()];
    let siege = siege_rewards['rank_' + $("#siege-ranking").val()];
    let gw_success_attacks = $("#guild-wings").val();
    let siege_first = $("input[name='siege-first']:checked").val();
    let siege_second = $("input[name='siege-second']:checked").val();

    let points_gw_per_day = (gw.battle + 3) * 2 + (gw.battle + 2) * 2 + (gw.battle + 1) * 2; // +6 rule
    let points_gw_win_per_week = gw.war * gw_success_attacks;
    let points_siege_first = (siege.points[siege_first - 1] / 100) * (20000 / siege_first) * .1; // 20k for win, 10k for 2nd place, 6.6k for 3rd place, 10% contribution ALWAYS
    let points_siege_second = (siege.points[siege_second - 1] / 100) * (20000 / siege_second) * .1; // 20k for win, 10k for 2nd place, 6.6k for 3rd place, 10% contribution ALWAYS

    for (const [key, value] of Object.entries(buildings)) {
        if($("#" + key + " #area").text() != "Guild"){ continue; }

        let upgrade_id = "#" + key + " #upgrade";
        let upgrade_max_id = "#" + key + " #upgrade-max";
        let days_id = "#" + key + " #days";
        let days_max_id = "#" + key + " #days-max";

        let upgrade_next = parseInt($(upgrade_id).text());
        let upgrade_max = parseInt($(upgrade_max_id).text());
        let days = 0;
        let days_max = 0;
        while(upgrade_next > 0){
            if(days % 7 == 0){ 
                upgrade_next += 150; // rainbowmon
                upgrade_next -= points_siege_first; // 1st siege, monday
            }
            else if(days % 7 == 3){
                upgrade_next -= points_siege_second; // 2nd siege, thursday
            }
            else if(days % 7 == 6){
                upgrade_next -= points_gw_win_per_week // weekly wins
            }
            upgrade_next -= points_gw_per_day
            days += 1;
        }
        while(upgrade_max > 0){
            if(days_max % 7 == 0){ 
                upgrade_max += 150; // rainbowmon
                upgrade_max -= points_siege_first; // 1st siege, monday
            }
            else if(days_max % 7 == 3){
                upgrade_max -= points_siege_second; // 2nd siege, thursday
            }
            else if(days_max % 7 == 6){
                upgrade_max -= points_gw_win_per_week // weekly wins
            }
            upgrade_max -= points_gw_per_day
            days_max += 1;
        }
        $(days_id).text(days);
        $(days_max_id).text(days_max);
    }
}