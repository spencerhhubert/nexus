package classification

//this is what the end user needs to construct and pass in for custom sorting methods. piece by color? sort out big from small? everythin in different lot?
type Profile struct {
    Name string
    Id int
    WhereGo map[string]Category
}

func BuildProfileFromJSON(json string) (Profile, error) {
    var profile Profile
    err := json.Unmarshal([]byte(json), &profile)
    if err != nil {
        return Profile{}, err //build out thing to translate to profile
    }
    return profile, nil
}
