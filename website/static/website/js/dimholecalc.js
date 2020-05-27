var profile = localStorage.getItem('profile_json')

$( document ).ready(function() {
    if(!profile){
        $('#profile-upload').html("<h2>No uploaded profile available. Please, <a href='" + upload_url + "'>upload your profile</a> first if you want to use all calculator functionalities.</h2>")
    }
    else{
        let monsters = JSON.parse(profile).unit_list;
        for(var index in monsters){
            let awakening_info = monsters[index].awakening_info
            if(!Array.isArray(awakening_info) ){ // no info -> empty array;  info -> object\
                let axp_needed = awakening_info.max_exp - awakening_info.exp
                let row_builder = '<tr>' +
                    '<td>' + base_monsters[awakening_info.unit_master_id] + '</td>' + 
                    '<td>' + awakening_info.exp + '</td>' + 
                    '<td>' + axp_needed + '</td>'

                for (const i of Array(5).keys()) {
                    let energy = Math.ceil(axp_needed / axp_per_level[i])
                    let days = Math.ceil(energy / 12) // 12 energy per day
                    row_builder += '<td>' + energy + '</td>' + 
                                    '<td>' + days + '</td>';
                }
                row_builder += '</tr>'
                $('#dimholecalc tbody').append(row_builder);
            }
        }
    }
});